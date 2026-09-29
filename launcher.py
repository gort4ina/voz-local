import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def start_application():
    print("==========================================")
    print("       VOZ LOCAL - LANÇADOR de PoC        ")
    print("==========================================\n")

    # --- CONFIGURAÇÃO DE CAMINHOS (FIX PARA ModuleNotFoundError) ---
    # Adicionamos a pasta 'backend' ao PYTHONPATH para que o Python encontre o módulo 'app'
    root_dir = os.getcwd()
    backend_dir = os.path.join(root_dir, "backend")
    os.environ["PYTHONPATH"] = backend_dir + os.pathsep + root_dir
    # ---------------------------------------------------------------

    # 1. Verificação de Token Hugging Face
    env_path = Path(".env")
    hf_token = None

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("HUGGINGFACE_TOKEN="):
                    hf_token = line.split("=")[1].strip()

    if not hf_token:
        print("⚠️  Token do Hugging Face não encontrado no arquivo .env")
        hf_token = input("Por favor, digite seu token do Hugging Face: ").strip()

        try:
            with open(env_path, "a") as f:
                f.write(f"\nHUGGINGFACE_TOKEN={hf_token}\n")
            print("✅ Token salvo com sucesso!\n")
        except Exception as e:
            print(f"❌ Não foi possível salvar o token: {e}\n")

    # 2. Caminhos e Comandos
    python_exe = sys.executable

    print("🚀 Iniciando API do Sistema...")
    # Agora chamamos 'app.main:app' porque adicionamos 'backend' ao PYTHONPATH
    api_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=root_dir,
        shell=True
    )

    print("🚀 Iniciando Worker de IA (Processamento)...")
    worker_process = subprocess.Popen(
        [python_exe, "-m", "app.workers.run"],
        cwd=backend_dir,
        shell=True
    )

    time.sleep(5)

    print("\n✅ Sistema pronto!")
    print("🌐 Abrindo a aplicação no seu navegador...")
    webbrowser.open("http://127.0.0.1:8000")

    print("\n------------------------------------------")
    print("⚠️  NÃO FECHE ESTA JANELA!")
    print("O sistema continuará rodando enquanto esta tela estiver aberta.")
    print("Pressione Ctrl+C para encerrar tudo.")
    print("------------------------------------------\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Encerrando aplicação...")
        api_process.terminate()
        worker_process.terminate()
        print("✅ Finalizado.")

if __name__ == "__main__":
    start_application()
