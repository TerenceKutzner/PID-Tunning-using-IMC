import pandas as pd
import numpy as np
import os
import re
import glob
import matplotlib.pyplot as plt
import matplotlib

# =========================
# CONFIG
# =========================
base_dir = os.path.dirname(os.path.abspath(__file__))
arquivos = glob.glob(os.path.join(base_dir, "01 - ValidData/monitor_output_test*.txt"))

fator_taucl = 1
CUT_TIME = 0.5
SMOOTH_WINDOW = 100

# ===== CONFIG VISUAL =====
plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 18,
    "axes.labelsize": 14,
    "axes.titleweight": "bold",
    "axes.labelweight": "bold",
    "legend.fontsize": 14,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14
})

# =========================
# ESTRUTURAS
# =========================
resultados_pid = []
parametros_processo = []

curvas = []
curvas_por_pwm = {}

# =========================
# LOOP NOS ARQUIVOS
# =========================
for arquivo in arquivos:

    tests = {}
    current_test = None

    with open(arquivo, "r") as f:
        for linha in f:
            linha = linha.strip()

            match = re.match(r"TEST\s+(\d+)", linha)
            if match:
                current_test = int(match.group(1))
                tests[current_test] = []
                continue

            if current_test is not None and ";" in linha:
                tests[current_test].append(linha)

    for test_id, linhas in tests.items():

        df = pd.DataFrame([l.split(";") for l in linhas])
        df = df.iloc[:, :5]
        df.columns = ["tempo", "rpm", "rpm_filtro", "pulsos", "pwm"]

        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna().reset_index(drop=True)

        if len(df) < 10:
            continue

        # tempo
        df["tempo"] = (df["tempo"] - df["tempo"].iloc[0]) / 1e6
        df = df[df["tempo"] > CUT_TIME].reset_index(drop=True)

        # filtro
        df["rpm_filtro"] = df["rpm_filtro"].rolling(SMOOTH_WINDOW, min_periods=1).mean()

        pwm_final = int(df["pwm"].iloc[-1])

        curvas.append({
            "arquivo": os.path.basename(arquivo),
            "teste": test_id,
            "tempo": df["tempo"].values,
            "rpm": df["rpm_filtro"].values,
            "pwm": pwm_final
        })

        curvas_por_pwm.setdefault(pwm_final, []).append(df[["tempo", "rpm_filtro"]].copy())

        # =========================
        # IDENTIFICAÇÃO
        # =========================
        df["delta_pwm"] = df["pwm"].diff()
        idx_step = df["delta_pwm"].abs().idxmax()

        tempo_step = df.loc[idx_step, "tempo"]

        CO_inicial = df["pwm"].iloc[0]
        CO_final = df["pwm"].iloc[-1]

        PV_inicial = df["rpm_filtro"].iloc[0]
        PV_final = df["rpm_filtro"].iloc[-1]

        delta_PV = PV_final - PV_inicial
        delta_CO = CO_final - CO_inicial

        gp = delta_PV / delta_CO if abs(delta_CO) > 1e-6 else 0

        # dead time
        threshold = PV_inicial + 0.02 * delta_PV
        df_pos = df[df["tempo"] >= tempo_step]

        candidatos = df_pos[df_pos["rpm_filtro"] >= threshold]

        if len(candidatos) == 0:
            deriv = np.gradient(df_pos["rpm_filtro"], df_pos["tempo"])
            idx_response = df_pos.index[np.argmax(deriv)]
        else:
            idx_response = candidatos.index[0]

        tempo_resposta = df.loc[idx_response, "tempo"]
        td = tempo_resposta - tempo_step

        # tau
        PV_63 = PV_inicial + 0.63 * delta_PV
        idx_63 = (df["rpm_filtro"] - PV_63).abs().idxmin()
        t_63 = df.loc[idx_63, "tempo"]

        tau = t_63 - tempo_resposta

        # =========================
        # SALVAR PARÂMETROS DO PROCESSO
        # =========================
        if gp != 0 and tau > 0:
            parametros_processo.append({
                "Arquivo": os.path.basename(arquivo),
                "Teste": test_id,
                "PWM": pwm_final,
                "K": gp,
                "tau": tau,
                "theta": td
            })

        # =========================
        # MÉTODOS PID
        # =========================
        if gp != 0 and tau > 0:

            theta = max(td, 1e-6)
            K = gp
            lam = fator_taucl * tau

            metodos = {}

            # IMC
            Kp = (2*tau + theta) / (K * (2*lam + theta))
            Ti = tau + theta/2
            Td = (tau * theta) / (2*tau + theta)
            metodos["IMC"] = (Kp, Kp/Ti, Kp*Td)

            # Lee
            Kp = tau / (K * (lam + theta))
            Ti = tau + theta/2
            Td = (theta**2) / (3 * (lam + theta))
            metodos["Lee"] = (Kp, Kp/Ti, Kp*Td)

            # SIMC
            Kp = (2*tau + theta) / (3 * K * theta)
            Ti = min(tau + theta, 8 * theta)
            Td = (tau * theta) / (2*tau + theta)
            metodos["SIMC"] = (Kp, Kp/Ti, Kp*Td)

            # IMC robusto
            Kp = (2.65 / K) * (tau/theta)**0.03
            Ti = 2.65 * theta
            Td = 1.72 * theta
            metodos["IMC_robusto"] = (Kp, Kp/Ti, Kp*Td)

            for nome, (Kp, Ki, Kd) in metodos.items():
                resultados_pid.append({
                    "Arquivo": os.path.basename(arquivo),
                    "Teste": test_id,
                    "Metodo": nome,
                    "PWM": pwm_final,
                    "Kp": Kp,
                    "Ki": Ki,
                    "Kd": Kd
                })

# =========================
# SALVAR RESULTADOS
# =========================

# PID
pd.DataFrame(resultados_pid).to_csv(
    os.path.join(base_dir, "03 - Results/01 - AnaliseDegrauV2/resultados_pid.txt"),
    index=False
)

# Parâmetros individuais
df_param = pd.DataFrame(parametros_processo)

df_param.to_csv(
    os.path.join(base_dir, "03 - Results/01 - AnaliseDegrauV2/parametros_individuais.txt"),
    index=False
)

# Média por PWM
df_media = df_param.groupby("PWM").agg({
    "K": ["mean", "std"],
    "tau": ["mean", "std"],
    "theta": ["mean", "std"]
}).round(4)

df_media.columns = ["_".join(col) for col in df_media.columns]

df_media.to_csv(
    os.path.join(base_dir, "03 - Results/01 - AnaliseDegrauV2/parametros_medios.txt")
)

print("Arquivos gerados com sucesso!")

# =========================
# CORES POR PWM
# =========================
pwms_unicos = sorted(set(c["pwm"] for c in curvas))

cmap = matplotlib.colormaps.get_cmap("tab20").resampled(len(pwms_unicos))
mapa_cores = {pwm: cmap(i) for i, pwm in enumerate(pwms_unicos)}

# =========================
# GRÁFICO 1
# =========================
plt.figure(figsize=(16, 10))

legendado = set()

for c in curvas:
    pwm = c["pwm"]
    cor = mapa_cores[pwm]

    label = None
    if pwm not in legendado:
        label = f"PWM {pwm}"
        legendado.add(pwm)

    if np.max(c["rpm"]) > 700:
        plt.plot(c["tempo"], c["rpm"], color=cor, linewidth=2.5, label=label)
    else:
        plt.plot(c["tempo"], c["rpm"], color=cor, alpha=0.6, label=label)

plt.xlabel("Tempo (s)")
plt.ylabel("RPM")
plt.title("Resposta do Motor ao Degrau")
plt.grid(True)

handles, labels = plt.gca().get_legend_handles_labels()
plt.legend(handles[::-1], labels[::-1],
           loc='center left',
           bbox_to_anchor=(1, 0.5))

# plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
plt.xticks(np.arange(0, 26, 1))     # de 0 a 10, passo 1
plt.yticks(np.arange(0, 105, 5))    # de 0 a 1000, passo 100

plt.savefig(os.path.join(base_dir, "03 - Results/01 - AnaliseDegrauV2/curvas_individuais.png"),
            dpi=300, bbox_inches="tight")

plt.show()

# =========================
# GRÁFICO 2
# =========================
plt.figure(figsize=(16, 10))

for pwm, lista_curvas in curvas_por_pwm.items():

    tempos = np.linspace(0, max(c["tempo"].max() for c in lista_curvas), 200)

    curvas_interp = [
        np.interp(tempos, c["tempo"], c["rpm_filtro"])
        for c in lista_curvas
    ]

    media = np.mean(curvas_interp, axis=0)

    plt.plot(tempos, media,
             color=mapa_cores[pwm],
             linewidth=2.5,
             label=f"PWM {pwm}")

plt.xlabel("Tempo (s)")
plt.ylabel("RPM")
plt.title("Média das Respostas aos Degraus")
plt.grid(True)

handles, labels = plt.gca().get_legend_handles_labels()
plt.legend(handles[::-1], labels[::-1],
           loc='center left',
           bbox_to_anchor=(1, 0.5))

# plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
plt.xticks(np.arange(0, 26, 1))     # de 0 a 10, passo 1
plt.yticks(np.arange(0, 105, 5))    # de 0 a 1000, passo 100
plt.xticks(np.arange(0, 26, 1))     # de 0 a 10, passo 1
plt.yticks(np.arange(0, 105, 5))    # de 0 a 1000, passo 100

plt.savefig(os.path.join(base_dir, "03 - Results/01 - AnaliseDegrauV2/media_pwm.png"),
            dpi=300, bbox_inches="tight")

plt.show()