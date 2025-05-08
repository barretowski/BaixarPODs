import os
import csv
import threading
import zipfile
import boto3
import requests
import mysql.connector
from threading import Lock
from datetime import datetime
from dotenv import load_dotenv
from s3 import gerar_url_pre_assinada
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

class ExtratorBanco:
    def __init__(self, input_csv, output_csv, db_config):
        self.input_csv = input_csv
        self.output_csv = output_csv
        self.db_config = db_config

    def extrair(self):
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)

            with open(self.input_csv, newline='') as csvfile_in:
                reader = csv.DictReader(csvfile_in, delimiter=';')
                total_linhas = sum(1 for _ in reader)

            with open(self.input_csv, newline='') as csvfile_in, open(self.output_csv, mode='w', newline='') as csvfile_out:
                reader = csv.DictReader(csvfile_in, delimiter=';')
                writer = csv.writer(csvfile_out, delimiter=';')
                writer.writerow(["AWB", "Encomenda ID", "Data", "Imagem"])

                linhas_encontradas = 0  # Contador para as linhas encontradas

                for linha in reader:
                    awb = linha.get("AWB", "").strip()
                    pedido = linha.get("Pedido", "").strip()
                    nota_fiscal = linha.get("Nota Fiscal", "").strip()

                    if not awb or not pedido or not nota_fiscal:
                        print(f"[SKIP] Linha incompleta: {linha}")
                        continue

                    query = """
                        SELECT e.awb, img.encoimg_id, img.encoimg_data, img.encoimg_img
                        FROM corrier.encomendas e
                        INNER JOIN corrier.encomendas_img img ON e.encoid = img.encoid
                        WHERE e.awb = %s AND e.pedido = %s AND e.nfiscal = %s AND img.encoimg_tipo = 0
                    """
                    cursor.execute(query, (awb, pedido, nota_fiscal))
                    
                    rows = cursor.fetchall()

                    if rows:
                        for row in rows:
                            writer.writerow([row["awb"], row["encoimg_id"], row["encoimg_data"], row["encoimg_img"]])
                            print(f"[OK] AWB {row['awb']} extraída")
                            linhas_encontradas += 1 
                    else:
                        print(f"[NOT FOUND] AWB: {awb}, Pedido: {pedido}, Nota Fiscal: {nota_fiscal}")

                print(f"[INFO] Total de encomendas encontradas e processadas: {linhas_encontradas} / {total_linhas}")  # Exibe a quantidade de linhas processadas

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"[ERRO] na extração do banco: {e}")


class BaixaPod:
    def __init__(self, nome_arquivo):
        self.nome_arquivo = os.path.join("..", "arquivos", nome_arquivo)
        self.output_dir = os.path.join("..", "pods_gerados")
        self.zip_name = os.path.join(self.output_dir, "PODs_" + nome_arquivo + ".zip")
        os.makedirs(self.output_dir, exist_ok=True)

        self.bucket_name = os.getenv("AWS_S3_BUCKET")
        session = boto3.Session(profile_name=os.getenv("AWS_PROFILE"))
        self.s3_client = session.client('s3', region_name=os.getenv('AWS_REGION'))
        self.db_config = {
            'host': os.getenv("DB_CORRIER_PRODUCAO"),
            'user': os.getenv("DB_CORRIER_USER"),
            'password': os.getenv("DB_CORRIER_PASS")
        }
        self.total_linhas_csv = 0
        self.total_encontradas = 0
        self.imagens_baixadas = 0
        self.imagens_falhadas = 0
        self.lock = Lock()
        self.awbs_sucesso = []
        self.awbs_falha = []

    def gerar_log(self):
        log_path = os.path.join(self.output_dir, "log_awbs_encontradas"+self.nome_arquivo+".txt")
        try:
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write("AWBs com imagens baixadas com sucesso:\n")
                for awb in self.awbs_sucesso:
                    log_file.write(f"[✔] {awb}\n")

                log_file.write("\nAWBs com falha ao baixar a imagem:\n")
                for awb in self.awbs_falha:
                    log_file.write(f"[✘] {awb}\n")

            print(f"[OK] Log de download salvo em: {log_path}")
        except Exception as e:
            print(f"[ERRO] ao salvar o log: {e}")

    def obter_informacoes(self, dados_csv):
        self.total_encontradas = len(dados_csv)
        try:
            with open(self.nome_arquivo, newline='') as csvfile_in:
                reader = csv.DictReader(csvfile_in, delimiter=';')
                self.total_linhas_csv = sum(1 for _ in reader)
        except Exception as e:
            print(f"[ERRO] ao contar linhas do CSV: {e}")
      

    def executar(self):
        inicio = datetime.now()
        csv_gerado_banco = os.path.join("..", "arquivos", "csv_gerado_banco.csv")
        
        extrator = ExtratorBanco(
            input_csv=self.nome_arquivo,
            output_csv=csv_gerado_banco,
            db_config=self.db_config
        )
        extrator.extrair()

        dados = self.ler_csv_entrada_personalizado(csv_gerado_banco)
        self.obter_informacoes(dados)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for linha in dados:
                awb = linha["AWB"]
                imagem_id = linha["Encomenda ID"]
                data_imagem = linha["Data"]

                future = executor.submit(self.baixar_imagem, 
                                        self.bucket_name, 
                                        awb, 
                                        imagem_id, 
                                        data_imagem, 
                                        self.output_dir)
                futures.append(future)

            for future in futures:
                future.result()

        self.gerar_log()
        self.comprimir_arquivos()
        fim = datetime.now()
        duracao = fim - inicio
        duracao_ms = duracao.total_seconds() * 1000

        print("-----------------------------------------------------------------------")
        print(f"[SUCESSO] ZIP gerado: {self.zip_name}")
        print(f"[INFO] Processo iniciado em: {inicio.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"[INFO] Processo finalizado em: {fim.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"[INFO] Tempo total de execução: {duracao} ({int(duracao_ms)} ms)")
        print("-----------------------------------------------------------------------")
        print(f"[RESUMO] Linhas no CSV original ..........: {self.total_linhas_csv}")
        print(f"[RESUMO] Encomendas encontradas no banco .: {self.total_encontradas}")
        print(f"[RESUMO] Imagens baixadas ................: {self.imagens_baixadas}")
        print(f"[RESUMO] Imagens não encontradas ............: {self.imagens_falhadas}")


    def ler_csv_entrada_personalizado(self, caminho_csv):
        try:
            with open(caminho_csv, newline='') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                return list(reader)
        except Exception as e:
            print(f"[ERRO] ao ler o CSV extraído: {e}")
            return []

    def baixar_pod(self, awb):
        try:
            nome_arquivo = f"{awb}.pdf"
            caminho_local = os.path.join(self.output_dir, nome_arquivo)
            self.s3_client.download_file(self.bucket_name, nome_arquivo, caminho_local)
            print(f"[✔] {nome_arquivo} baixado")
        except Exception as e:
            print(f"[ERRO] ao baixar {awb}: {e}")

    def baixar_imagem(self, bucket, awb, imagem_id, data_imagem, pasta_destino):
        nome_imagem = f"{awb}_{imagem_id}.jpg"
        caminho_arquivo_local = os.path.join(pasta_destino, nome_imagem)
        chave_s3 = f"{data_imagem[:4]}/{data_imagem[5:7]}/{data_imagem[8:10]}/{imagem_id}"

        if os.path.exists(caminho_arquivo_local):
            print(f"[INFO] Arquivo já existe: {caminho_arquivo_local}")
            with self.lock:
                self.imagens_baixadas += 1
                self.awbs_sucesso.append(awb)
            return

        url = gerar_url_pre_assinada(bucket, chave_s3)
        if not url:
            print(f"[ERRO] Não foi possível gerar a URL para {chave_s3}")
            with self.lock:
                self.imagens_falhadas += 1
                self.awbs_falha.append(awb)
            return

        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(caminho_arquivo_local, 'wb') as f:
                f.write(response.content)
            print(f"[SUCESSO] Imagem salva: {caminho_arquivo_local}")
            with self.lock:
                self.imagens_baixadas += 1
                self.awbs_sucesso.append(awb)
        except requests.RequestException as e:
            print(f"[ERRO] Falha ao baixar {chave_s3}: {e}")
            with self.lock:
                self.imagens_falhadas += 1
                self.awbs_falha.append(awb)

    def comprimir_arquivos(self):
        try:
            nome_base = os.path.basename(self.zip_name)
            nome_sem_extensao = nome_base.split('.')[0]  # Pega só o nome antes do primeiro ponto
            self.zip_name = os.path.join(self.output_dir, f"{nome_sem_extensao}.zip")

            with zipfile.ZipFile(self.zip_name, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
                for root, _, files in os.walk(self.output_dir):
                    for file in files:
                        if file == os.path.basename(self.zip_name):
                            continue
                        caminho_completo = os.path.join(root, file)
                        zipf.write(caminho_completo, arcname=file)
                        os.remove(caminho_completo)
            print(f"[OK] Arquivos compactados e removidos com sucesso.")
        except Exception as e:
            print(f"[ERRO] ao gerar ZIP: {e}")








