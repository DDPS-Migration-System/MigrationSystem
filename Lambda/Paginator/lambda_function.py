import boto3

def lambda_handler(event, context):
    # API를 호출한 유저의 닉네임을 가져옴
    username = event["queryStringParameters"]["UserName"]
    # 인스턴스 정보를 관리하는 DB에 존재하는 elements를 가져옴
    
    # 가져온 elements들 중, 유저의 닉네임이 일치하는 elements만 리턴
    return {
        "statusCode": 200,
        "message": "Migration Complete"
    }