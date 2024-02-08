import boto3

def lambda_handler(event, context):
    # API를 통해 생성하고자 하는 인스턴스 정보를 얻어옴 (Name, Userdata, Port, Security, hardware size 등)
    # hardware size를 통해 최적의 인스턴스를 선택
    # Name, Userdata, Security 정보를 사용해 인스턴스를 프로비저닝
    # 생성된 인스턴스를 인스턴스 관리 DB에 기록
    # 생성된 인스턴스의 CPU, MEM Usage를 체크하는 EventBridge Alarm, Rule을 생성 후 Migrator에 연결
    # 웹페이지를 지원한다면 ALB에 연결
    return {
        "statusCode": 200,
        "message": "Migration Complete"
    }