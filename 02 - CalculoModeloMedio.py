import pandas as pd

# Ler o arquivo
df = pd.read_csv("03 - Results/01 - AnaliseDegrauV2/parametros_medios.txt")

# Filtrar região linear (ajuste aqui se quiser mudar)
df_filtrado = df[(df["PWM"] >= 60) & (df["PWM"] <= 200)]

# Calcular médias
K_mean = df_filtrado["K_mean"].mean()
tau_mean = df_filtrado["tau_mean"].mean()
theta_mean = df_filtrado["theta_mean"].mean()

# Criar DataFrame com resultado
resultado = pd.DataFrame({
    "K_medio": [K_mean],
    "tau_medio": [tau_mean],
    "theta_medio": [theta_mean]
})

# Salvar em arquivo
resultado.to_csv("03 - Results/02 - CalculoModeloMedio/valores_medios.txt", index=False)

print("Valores calculados:")
print(resultado)