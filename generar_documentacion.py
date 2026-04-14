import os
import sys
import subprocess

def generar_documentacion():
    # Ruta a la carpeta docs
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')
    
    # Verifica si la carpeta docs existe
    if not os.path.exists(docs_dir):
        print("La carpeta 'docs' no existe. Ejecuta 'sphinx-quickstart' para configurarla.")
        sys.exit(1)
    
    # Ejecuta el comando para generar la documentación en HTML
    try:
        subprocess.run(['make', 'html'], cwd=docs_dir, check=True)
        print("Documentación generada exitosamente.")
    except subprocess.CalledProcessError as e:
        print(f"Error al generar la documentación: {e}")
        sys.exit(1)

if __name__ == '__main__':
    generar_documentacion()
