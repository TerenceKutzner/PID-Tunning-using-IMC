import csv

input_file = "03 - Results/01 - AnaliseDegrauV2/parametros_medios.txt"
output_file = "03 - Results/04 - GeradorTabelasLatex/code_parametros_medios.txt"

def format_4(value):
    return f"{float(value):.4f}".replace('.', ',')

with open(input_file, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)

    latex_lines = []

    latex_lines.append("\\begin{center}")
    latex_lines.append("\\resizebox{\\columnwidth}{!}{%")
    latex_lines.append(
        "\\begin{tabular}{>{\\centering\\hspace{0pt}}m{0.1\\linewidth}"
        ">{\\centering\\hspace{0pt}}m{0.13\\linewidth}"
        ">{\\centering\\hspace{0pt}}m{0.13\\linewidth}"
        ">{\\centering\\hspace{0pt}}m{0.13\\linewidth}"
        ">{\\centering\\hspace{0pt}}m{0.13\\linewidth}"
        ">{\\centering\\hspace{0pt}}m{0.13\\linewidth}"
        ">{\\centering\\arraybackslash\\hspace{0pt}}m{0.13\\linewidth}}"
    )

    latex_lines.append("\\toprule")

    # ===== CABEÇALHO LIMPO =====
    header_latex = [
        "\\textbf{PWM}",
        "\\textbf{$\\bar{K}$}",
        "\\textbf{$\\sigma_{K}$}",
        "\\textbf{$\\bar{\\tau}$ (s)}",
        "\\textbf{$\\sigma_{\\tau}$ (s)}",
        "\\textbf{$\\bar{\\theta}$ (s)}",
        "\\textbf{$\\sigma_{\\theta}$ (s)}"
    ]

    latex_lines.append(" & ".join(header_latex) + " \\\\")
    latex_lines.append("\\midrule")

    # ===== DADOS =====
    for row in reader:
        pwm = row[0]

        K_mean = format_4(row[1])
        K_std  = format_4(row[2])

        tau_mean   = format_4(row[3])
        tau_std    = format_4(row[4])
        theta_mean = format_4(row[5])
        theta_std  = format_4(row[6])

        latex_lines.append(
            f"{pwm} & {K_mean} & {K_std} & {tau_mean} & {tau_std} & {theta_mean} & {theta_std} \\\\"
        )

    latex_lines.append("\\bottomrule")
    latex_lines.append("\\end{tabular}")
    latex_lines.append("}")

    # ===== LEGENDA =====
    latex_lines.append(
        "\\tabcaption{Parâmetros médios e desvios padrão do modelo de primeira ordem com atraso (FOPDT) para diferentes valores de PWM.}"
    )
    latex_lines.append("\\label{tb:parametros_medios}")
    latex_lines.append("\\end{center}")

with open(output_file, 'w') as f:
    for line in latex_lines:
        f.write(line + "\n")

print(f"Arquivo '{output_file}' gerado com sucesso!")