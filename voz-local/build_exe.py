import os
import subprocess
import sys

def build():
    print("=== Iniciando Processo de Build do Executável ===")

    # 1. Instalar Dependências Necessárias
    print("\n📦 Instalando dependências de build e runtime...")
    dependencies = [
        "pyinstaller",
        "python-magic-bin", # Essencial para Windows
        "python-multipart",   # Necessário para Upload de arquivos no FastAPI
        "fastapi",
        "uvicorn",
        "torch",
        "faster-whisper",
        "pyannote.audio"
    ]

    for dep in dependencies:
        print(f"Instalando {dep}...")
        subprocess.run([sys.executable, "-m", "pip", "install", dep])

    # 2. Comando do PyInstaller
    frontend_dist = "frontend/dist/voz-local/browser"

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--name", "VozLocal",
        "--collect-all", "fastapi",
        "--collect-all", "uvicorn",
        "--collect-all", "torch",
        "--add-data", f"{frontend_dist}{os.pathsep}frontend/dist/voz-local/browser",
        "--add-data", "backend/app{os.pathsep}backend/app",
        "launcher.py"
    ]

    print("\n🔨 Compilando executável... (Isso pode demorar vários minutos)")
    subprocess.run(cmd)

    print("\n==========================================================")
    print("✅ BUILD CONCLUÍDO!")
    print("O executável está na pasta: dist/VozLocal/VozLocal.exe")
    print("\n⚠️ IMPORTANTE PARA O TESTE FINAL:")
    print("1. Baixe o FFmpeg (ffmpeg.exe) e coloque-o dentro da pasta dist/VozLocal/")
    print("2. Envie a pasta 'dist/VozLocal' compactada (ZIP) para a pessoa testar.")
    print("==========================================================")

if __name__ == "__main__":
    build()
