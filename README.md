# PodPy

**PodPy** é uma ferramenta em Python para baixar, organizar e gerenciar comprovantes de entrega (PODs - *Proof of Delivery*). Ideal para transportadoras, sistemas de logística e ERPs que necessitam automatizar a coleta e verificação de documentos de entrega.

## 🚀 Funcionalidades

- 🔍 Busca automatizada de imagens de PODs em diretórios ou repositórios remotos.
- ⬇️ Download e salvamento local dos arquivos encontrados.
- 🧠 Identificação de PODs por nome de arquivo, número da entrega, ou outros critérios.
- 📁 Organização automática por pastas (ex: por data ou transportadora).
- 📝 Geração de logs sobre PODs encontrados, ausentes ou duplicados.

## 📦 Requisitos

- Python 3.8+
- Bibliotecas utilizadas:
  - `os`
  - `logging`
  - `shutil`
  - `argparse` (caso utilize interface CLI)
  - Outras conforme sua implementação (ex: `pandas`, `requests`)

Instale as dependências com:

bash
pip install -r requirements.txt

## ⚙️ Como usar
Modo básico:
bash
Copiar
Editar
python podpy.py --input pedidos.csv --output ./pods_encontrados
Parâmetros:
Parâmetro	Descrição
--input	Caminho para o arquivo CSV ou JSON com os dados dos pedidos
--output	Diretório onde os PODs serão salvos
--log	(Opcional) Caminho para o arquivo de log

## 🗂️ Estrutura do Projeto
css
Copiar
Editar
PodPy/
├── src/
│   ├── podpy.py
│   ├── utils.py
│   └── ...
├── logs/
│   └── podpy.log
├── tests/
├── requirements.txt
└── README.md
🧪 Testes

✨ Contribuições
Contribuições são bem-vindas! Sinta-se livre para abrir issues ou enviar pull requests.
Desenvolvido por Paulo Henrique
