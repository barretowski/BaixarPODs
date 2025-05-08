import sys
from baixa_pod import BaixaPod
from dotenv import load_dotenv

def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <nomeArquivo.csv>")
        sys.exit(1)

    nome_arquivo = sys.argv[1]

    load_dotenv()
    executor = BaixaPod(nome_arquivo)
    executor.executar()

if __name__ == '__main__':
    main()
