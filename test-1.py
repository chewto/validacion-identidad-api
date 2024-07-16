import subprocess

comando = 'python main.py'  # Reemplaza 'comando_a_ejecutar' con el comando que deseas ejecutar en CMD
resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)

print(resultado)

# if resultado.returncode == 0:
#     print("Comando ejecutado correctamente:")
#     print(resultado)
# else:
#     print("Error al ejecutar el comando:")
#     print(resultado.stderr)
