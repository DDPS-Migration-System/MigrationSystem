import boto3
from variable import *

# Cognito Identity Provider 클라이언트 생성
cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

# 사용자 풀 ID와 새 사용자의 세부 정보를 설정
user_pool_name = f'{prefix}-user-pool'

def lambda_handler(event, context):
    user_pool_id = None
    response = cognito_client.list_user_pools(MaxResults=60)  # MaxResults는 필요에 따라 조정하세요
    for pool in response['UserPools']:
        if pool['Name'] == pool_name:
            user_pool_id = pool['Id']
    username = event['queryStringParameters']['UserName']
    password = event['queryStringParameters']['Password']
    email = event['queryStringParameters']['Email']
    isAdmin = event['queryStringParameters']['isAdmin']

    try:
        # 새 사용자 생성 및 사용자 풀에 등록
        response = client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                },
                {
                    'Name': 'email_verified',
                    'Value': 'True'
                },
                {
                    'Name': 'custom:isAdmin',
                    'Value': str(isAdmin)
                }
            ],
            TemporaryPassword=password,
            ForceAliasCreation=False,
            MessageAction='SUPPRESS'  # 이메일 검증 메시지를 보내지 않음
        )
        print("User created successfully:", response)

        # 사용자 비밀번호 설정 (선택적)
        response = client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True  # 임시 비밀번호가 아닌 영구 비밀번호로 설정
        )
        print("Password set successfully for the user.")
    except client.exceptions.UsernameExistsException as e:
        print("User already exists:", e)
    except Exception as e:
        print("Error creating user:", e)
    
    return {
        "statusCode": 200,
        "message": json.dumps(response)
    }
