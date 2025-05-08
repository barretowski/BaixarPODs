import boto3
from botocore.exceptions import ClientError

def gerar_url_pre_assinada(bucket, key, expiracao=3600):
    """
    Gera uma URL pré-assinada para download de um objeto do S3.

    :param bucket: Nome do bucket
    :param key: Caminho do objeto no bucket
    :param expiracao: Tempo de expiração da URL em segundos (padrão: 1 hora)
    :return: URL pré-assinada ou None se falhar
    """
    s3 = boto3.client('s3')
    try:
        url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': bucket, 'Key': key},
                                        ExpiresIn=expiracao)
        return url
    except ClientError as e:
        print(f"[ERRO] ao gerar URL para {key}: {e}")
        return None
