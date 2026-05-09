import pandas as pd
import numpy as np
import os
import re
import glob
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
base_dir = os.path.dirname(os.path.abspath(__file__))
arquivos = glob.glob(os.path.join(base_dir, "01 - ValidData/monitor_output_test*.txt"))

fator_taucl = 1
CUT_TIME = 0.5
SMOOTH_WINDOW = 3
LIMITE_PICO = 700  # RPM limite para detectar erro

resultados = []
curvas = []
curvas_por_pwm = {}
problemas = []

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

    # =========================
    # PROCESSAR TESTES
    # =========================
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

        # =========================
        # DETECÇÃO DE PICOS
        # =========================
        pico = df["rpm_filtro"].max()

        if pico > LIMITE_PICO:
            print("\n PICO DETECTADO!")
            print(f"Arquivo: {os.path.basename(arquivo)}")
            print(f"Teste: {test_id}")
            print(f"RPM pico: {pico:.2f}")

            problemas.append({
                "arquivo": os.path.basename(arquivo),
                "teste": test_id,
                "rpm_pico": pico
            })

        rpm_final = df["rpm_filtro"].tail(10).mean()
        pwm_final = int(df["pwm"].iloc[-1])

        # guardar curva
        curvas.append({
            "arquivo": os.path.basename(arquivo),
            "teste": test_id,
            "tempo": df["tempo"].values,
            "rpm": df["rpm_filtro"].values
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
            idx_local = np.argmax(deriv)
            idx_response = df_pos.index[idx_local]
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
                resultados.append({
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
df_res = pd.DataFrame(resultados)
df_res.to_csv(os.path.join(base_dir, "03 - Results/01 - IdentificadorErrosDegrau/resultados_pid.txt"), index=False)

# salvar problemas
if problemas:
    df_prob = pd.DataFrame(problemas)
    df_prob.to_csv(os.path.join(base_dir, "03 - Results/01 - IdentificadorErrosDegrau/problemas_detectados.txt"), index=False)
    print("\nArquivo problemas_detectados.txt gerado!")

print("Arquivo resultados_pid.txt gerado!")

# =========================
# PLOT DEBUG (CURVAS)
# =========================
plt.figure(figsize=(12, 6))

for c in curvas:

    label = f"{c['arquivo']} | Teste {c['teste']}"

    if np.max(c["rpm"]) > LIMITE_PICO:
        plt.plot(c["tempo"], c["rpm"], linewidth=2, label=label + " ⚠️")
    else:
        plt.plot(c["tempo"], c["rpm"], alpha=0.3)

plt.xlabel("Tempo (s)")
plt.ylabel("RPM")
plt.title("Curvas individuais (picos destacados)")
plt.grid(True)
plt.legend()
plt.show()

# =========================
# PLOT MÉDIA POR PWM
# =========================
plt.figure(figsize=(12, 6))

for pwm, lista_curvas in curvas_por_pwm.items():

    tempos = np.linspace(0, max(c["tempo"].max() for c in lista_curvas), 200)

    curvas_interp = []

    for c in lista_curvas:
        interp = np.interp(tempos, c["tempo"], c["rpm_filtro"])
        curvas_interp.append(interp)

    media = np.mean(curvas_interp, axis=0)

    plt.plot(tempos, media, label=f"PWM {pwm}")

plt.xlabel("Tempo (s)")
plt.ylabel("RPM médio")
plt.title("Resposta média por PWM")
plt.grid(True)
plt.legend()
plt.show()