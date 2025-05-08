import boto3
from botocore.exceptions import NoCredentialsError, ClientError

try:
    # Cria uma sessão com o perfil que já possui MFA configurado
    session = boto3.Session(profile_name="mfa")

    # Cria o cliente S3 com a sessão e região apropriada
    s3_client = session.client('s3', region_name='sa-east-1')

    # Gera a URL pré-assinada
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': 'ics-pod-totex',
            'Key': '2024/11/18/696822575'
        },
        ExpiresIn=3600
    )
    print(url)

except NoCredentialsError:
    print("Credenciais não encontradas!")
except ClientError as e:
    print(f"AWS erro: {e}")
except Exception as e:
    print(f"Erro inesperado: {e}")
