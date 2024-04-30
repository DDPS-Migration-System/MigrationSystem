import boto3
import json
from variables import *

# DynamoDB 서비스 리소스 생성
dynamodb = boto3.resource('dynamodb')

# 쿼리할 테이블 선택
table = dynamodb.Table(f'{prefix}DynamoDB')

def lambda_handler(event, context):
    # API를 호출한 유저의 닉네임을 가져옴
    username = event["queryStringParameters"]["UserName"]

    # 인스턴스 정보를 관리하는 DB에 존재하는 elements를 가져옴
    response = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('UserName').eq(username)
    )
    items = response['Items']
    # 가져온 elements들 중, 유저의 닉네임이 일치하는 elements만 리턴
    page = []
    for item in items:
        if username == item['UserName']:
            page.append(item)
    return {
        "statusCode": 200,
        "message": json.dumps(page)
    }