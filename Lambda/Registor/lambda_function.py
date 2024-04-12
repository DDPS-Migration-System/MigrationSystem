import boto3
import json
from botocore.exceptions import ClientError
from variables import *

# Cognito Identity Provider 클라이언트 생성
cognito_client = boto3.client('cognito-idp')

ssm_client = boto3.client('ssm')

# 사용자 풀 ID와 새 사용자의 세부 정보를 설정
user_pool_name = f'{prefix}-user-pool'

def get_ssm_parameter(parameter_name):
    try:
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except ClientError as e:
        print(f"Failed to retrieve {parameter_name} from SSM Parameter Store: {e}")
        raise e

def lambda_handler(event, context):
    user_pool_id = get_ssm_parameter('stablespot-user-pool-id')
    response = cognito_client.list_user_pools(MaxResults=60)  # MaxResults는 필요에 따라 조정하세요
    body = json.loads(event['body'])
    username = body['nickname']
    password = body['password']
    email = body['email']
    isAdmin = body['isAdmin']

    try:
        # 새 사용자 생성 및 사용자 풀에 등록
        response = cognito_client.admin_create_user(
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
        response = cognito_client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True  # 임시 비밀번호가 아닌 영구 비밀번호로 설정
        )
        print("Password set successfully for the user.:", response)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "User created Succesfully."})
        }
        

    except cognito_client.exceptions.UsernameExistsException as e:
        return {
            "statusCode": 409,
            "body": json.dumps({"errMessage": "User already exists.", "error": str(e)})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"errMessage": "Error creating user.", "error": str(e)})
        }
