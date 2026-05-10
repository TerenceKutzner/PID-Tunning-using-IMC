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

input_dir = os.path.join(
    base_dir,
    "04 - PID Response Data"
)

output_dir = os.path.join(
    base_dir,
    "03 - Results/05 - PID Response"
)

os.makedirs(output_dir, exist_ok=True)

# remove primeiros segundos
CUT_TIME = 0.5

# suavização
SMOOTH_WINDOW = 50

# RPM máximo esperado do motor
RPM_MAX_VALIDO = 105

# =========================
# CONFIG VISUAL
# =========================
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
# CORES POR TARGET RPM
# =========================
targets_unicos = np.arange(0, 105, 5)

cmap = matplotlib.colormaps.get_cmap("tab20")

mapa_cores_target = {
    rpm: cmap(i % 20)
    for i, rpm in enumerate(targets_unicos)
}

# =========================
# LISTA CURVAS REMOVIDAS
# =========================
curvas_removidas = []

# =========================
# LISTA DE PASTAS
# =========================
pastas_metodos = sorted(
    glob.glob(os.path.join(input_dir, "*"))
)

# =========================
# LOOP MÉTODOS
# =========================
for pasta in pastas_metodos:

    nome_pasta = os.path.basename(pasta)

    metodo_match = re.search(
        r"teste\s+(.*)",
        nome_pasta,
        re.IGNORECASE
    )

    if metodo_match:
        metodo = metodo_match.group(1).strip()
    else:
        metodo = nome_pasta

    arquivos = glob.glob(
        os.path.join(pasta, "monitor_output_test*.txt")
    )

    curvas = []

    # =========================
    # LOOP ARQUIVOS
    # =========================
    for arquivo in arquivos:

        tests = {}
        current_test = None

        # =========================
        # LEITURA ARQUIVO
        # =========================
        with open(arquivo, "r") as f:

            for linha in f:

                linha = linha.strip()

                match = re.match(
                    r"TEST\s+(\d+)",
                    linha
                )

                if match:
                    current_test = int(match.group(1))
                    tests[current_test] = []
                    continue

                if current_test is not None and ";" in linha:
                    tests[current_test].append(linha)

        # =========================
        # LOOP TESTES
        # =========================
        for test_id, linhas in tests.items():

            # dataframe
            df = pd.DataFrame(
                [l.split(";") for l in linhas]
            )

            df = df.iloc[:, :6]

            df.columns = [
                "tempo",
                "rpm",
                "rpm_filtro",
                "rpm_target",
                "pulsos",
                "pwm"
            ]

            # =========================
            # CONVERSÃO NUMÉRICA
            # =========================
            for col in df.columns:
                df[col] = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

            # remove NaN
            df = df.dropna().reset_index(drop=True)

            if len(df) < 10:
                continue

            # =========================
            # TEMPO
            # =========================
            df["tempo"] = (
                df["tempo"] - df["tempo"].iloc[0]
            ) / 1e6

            # remove lixo inicial
            df = df[
                df["tempo"] > CUT_TIME
            ].reset_index(drop=True)

            if len(df) < 10:
                continue

            # reinicia tempo
            df["tempo"] = (
                df["tempo"] - df["tempo"].iloc[0]
            )

            # =========================
            # FILTRO
            # =========================
            df["rpm_filtro"] = (
                df["rpm_filtro"]
                .rolling(
                    SMOOTH_WINDOW,
                    min_periods=1
                )
                .mean()
            )

            # =========================
            # VALIDAÇÃO CURVA
            # =========================
            rpm_max = df["rpm_filtro"].max()
            rpm_min = df["rpm_filtro"].min()

            if (
                rpm_max > RPM_MAX_VALIDO or
                rpm_min < -10
            ):

                curvas_removidas.append({
                    "metodo": metodo,
                    "arquivo": os.path.basename(arquivo),
                    "teste": test_id,
                    "rpm_max": rpm_max,
                    "rpm_min": rpm_min
                })

                continue

            # =========================
            # TARGET FINAL
            # =========================
            target_final = int(
                round(df["rpm_target"].iloc[-1] / 5) * 5
            )

            curvas.append({
                "arquivo": os.path.basename(arquivo),
                "teste": test_id,
                "tempo": df["tempo"].values,
                "rpm": df["rpm_filtro"].values,
                "target": df["rpm_target"].values,
                "target_final": target_final
            })

    # =========================
    # PLOT
    # =========================
    plt.figure(figsize=(16, 10))

    targets_legendados = set()
    legenda_target = False

    for c in curvas:

        target_final = c["target_final"]

        cor = mapa_cores_target.get(
            target_final,
            "black"
        )

        mostrar_label = (
            target_final not in targets_legendados
        )

        # =========================
        # RPM REAL
        # =========================
        plt.plot(
            c["tempo"],
            c["rpm"],
            color=cor,
            linewidth=2.0,
            alpha=0.7,
            label=f"{target_final} RPM"
            if mostrar_label else None
        )

        targets_legendados.add(target_final)

        # =========================
        # SETPOINT
        # =========================
        if not legenda_target:

            plt.plot(
                c["tempo"],
                c["target"],
                linestyle="--",
                linewidth=2.5,
                color="black",
                label="Setpoint"
            )

            legenda_target = True

        else:

            plt.plot(
                c["tempo"],
                c["target"],
                linestyle="--",
                linewidth=1.5,
                color="black",
                alpha=0.3
            )

    # =========================
    # VISUAL
    # =========================
    plt.xlabel("Tempo (s)")
    plt.ylabel("RPM")

    plt.title(
        f"Resposta PID - Método {metodo}"
    )

    plt.grid(True)

    plt.legend(
        loc='center left',
        bbox_to_anchor=(1, 0.5)
    )

    plt.xticks(np.arange(0, 36, 1))
    plt.yticks(np.arange(0, 105, 5))

    # =========================
    # SAVE
    # =========================
    nome_saida = (
        f"resposta_pid_{metodo.lower()}.png"
    )

    plt.savefig(
        os.path.join(output_dir, nome_saida),
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

# =========================
# RELATÓRIO FINAL
# =========================
print("\n===================================")
print("CURVAS REMOVIDAS")
print("===================================")

if len(curvas_removidas) == 0:

    print("Nenhuma curva removida.")

else:

    for c in curvas_removidas:

        print(
            f"[{c['metodo']}] "
            f"{c['arquivo']} | "
            f"TEST {c['teste']} | "
            f"RPM max = {c['rpm_max']:.1f} | "
            f"RPM min = {c['rpm_min']:.1f}"
        )

print("\nGráficos PID gerados com sucesso!")