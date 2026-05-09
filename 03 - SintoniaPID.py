import pandas as pd

# =========================
# Ler valores médios
# =========================
df = pd.read_csv("03 - Results/02 - CalculoModeloMedio/valores_medios.txt")

K = df["K_medio"].values[0]
tau = df["tau_medio"].values[0]
theta = df["theta_medio"].values[0]

# Lambdas
lambda_imc = theta
lambda_lee = theta / 3

# =========================
# Métodos
# =========================
resultados = []

# IMC
Kp = (2*tau + theta) / (K * (2*lambda_imc + theta))
Ti = tau + theta/2
Td = (tau * theta) / (2*tau + theta)
resultados.append(["IMC", "Rivera et al. (1986)", Kp, Ti, Td])

# Lee
Kp = tau / (K * (lambda_lee + theta))
Ti = tau + theta/2
Td = (theta**2) / (3 * (lambda_lee + theta))
resultados.append(["Malha fechada", "Lee et al. (1998)", Kp, Ti, Td])

# SIMC
Kp = (2*tau + theta) / (3 * K * theta)
Ti = min(tau + theta, 8*theta)
Td = (tau * theta) / (2*tau + theta)
resultados.append(["SIMC", "Skogestad (2003)", Kp, Ti, Td])

# IMC Robusto
Kp = (2.65 / K) * (tau/theta)**0.03
Ti = 2.65 * theta
Td = 1.72 * theta
resultados.append(["IMC Robusto", "Vilanova (2008)", Kp, Ti, Td])

df_pid = pd.DataFrame(resultados, columns=["Metodo", "Autor", "Kp", "Ti", "Td"])

# Converter para Ki, Kd
df_ganhos = df_pid.copy()
df_ganhos["Ki"] = df_ganhos["Kp"] / df_ganhos["Ti"]
df_ganhos["Kd"] = df_ganhos["Kp"] * df_ganhos["Td"]
df_ganhos = df_ganhos.drop(columns=["Ti", "Td"])

# =========================
# Função formato brasileiro
# =========================
def fmt(x):
    return f"{x:.4f}".replace(".", ",")

# =========================
# Gerar tabela LaTeX (Kp Ti Td)
# =========================
with open("03 - Results/03 - SintoniaPID/tabela_pid_custom.tex", "w") as f:
    f.write("\\begin{center}\n")
    f.write("\\resizebox{\\columnwidth}{!}{%\n")
    f.write("\\begin{tabular}{>{\\centering}m{0.2\\linewidth}>{\\centering}m{0.25\\linewidth}>{\\centering}m{0.18\\linewidth}>{\\centering}m{0.18\\linewidth}>{\\centering\\arraybackslash}m{0.18\\linewidth}}\n")
    f.write("\\toprule\n")
    f.write("\\textbf{Método} & \\textbf{Autor} & \\textbf{$K_p$} & \\textbf{$T_i$ (s)} & \\textbf{$T_d$ (s)} \\\\\n")
    f.write("\\midrule\n")

    for _, row in df_pid.iterrows():
        f.write(f"{row['Metodo']} & {row['Autor']} & {fmt(row['Kp'])} & {fmt(row['Ti'])} & {fmt(row['Td'])} \\\\\n")

    f.write("\\bottomrule\n")
    f.write("\\end{tabular}\n")
    f.write("}\n")
    f.write("\\tabcaption{Parâmetros dos controladores PID obtidos pelos métodos de sintonia.}\n")
    f.write("\\label{tb:pid_param}\n")
    f.write("\\end{center}\n")

# =========================
# Gerar tabela LaTeX (Kp Ki Kd)
# =========================
with open("03 - Results/03 - SintoniaPID/tabela_ganhos_custom.tex", "w") as f:
    f.write("\\begin{center}\n")
    f.write("\\resizebox{\\columnwidth}{!}{%\n")
    f.write("\\begin{tabular}{>{\\centering}m{0.2\\linewidth}>{\\centering}m{0.25\\linewidth}>{\\centering}m{0.18\\linewidth}>{\\centering}m{0.18\\linewidth}>{\\centering\\arraybackslash}m{0.18\\linewidth}}\n")
    f.write("\\toprule\n")
    f.write("\\textbf{Método} & \\textbf{Autor} & \\textbf{$K_p$} & \\textbf{$K_i$} & \\textbf{$K_d$} \\\\\n")
    f.write("\\midrule\n")

    for _, row in df_ganhos.iterrows():
        f.write(f"{row['Metodo']} & {row['Autor']} & {fmt(row['Kp'])} & {fmt(row['Ki'])} & {fmt(row['Kd'])} \\\\\n")

    f.write("\\bottomrule\n")
    f.write("\\end{tabular}\n")
    f.write("}\n")
    f.write("\\tabcaption{Ganhos equivalentes dos controladores PID.}\n")
    f.write("\\label{tb:pid_ganhos}\n")
    f.write("\\end{center}\n")

print("Tabelas LaTeX no seu formato geradas!")