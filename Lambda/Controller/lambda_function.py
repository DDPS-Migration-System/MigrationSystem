import boto3
import json
from boto3.dynamodb.conditions import Attr
from variables import *

# DynamoDB 서비스 리소스 생성
dynamodb = boto3.resource('dynamodb')

# 쿼리할 테이블 선택
table = dynamodb.Table(f'{prefix}DynamoDB')

def lambda_handler(event, context):
    try:
        # API를 호출한 유저의 닉네임을 가져옴
        body = json.loads(event['body'])
        username = body["UserName"].strip()

        # DynamoDB에서 필터 조건을 사용하여 항목 조회
        response = table.scan(
            FilterExpression=Attr('UserName').eq(username)
        )
        items = response['Items']
        print("필터링된 항목: ", items)
        
        # 변환된 데이터 구조로 변환
        page = [
            {
                "servername": item.get('InstanceName'),
                "id": item.get('InstanceId'),
                "type": item.get('InstanceType'),
                "isRunning": item.get('isRunning'),
                "address": item.get('IpAddress'),
                "isWeb": item.get("isWeb"),
                "port": item.get("port"),
                "SpotReqId": item.get("SpotReqId")
            }
            for item in items
        ]
        
        return {
            "statusCode": 200,
            "body": json.dumps(page)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
