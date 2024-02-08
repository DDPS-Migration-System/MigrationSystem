import boto3
import json
from variables import *

ec2_client = boto3.client('ec2')
dynamodb = boto3.resource('dynamodb')

table = dynamodb.Table(f'{prefix}DynamoDB')

def lambda_handler(event, context):
    # 마이그레이션 종류 얻어옴
    migration_type = event["queryStringParameters"]["migrationType"]
    # 인터럽트가 발생한 인스턴스의 ID 얻어옴
    instance_id = event["queryStringParameters"]["instanceId"]
    dynamo_response = table.get_item(
        Key={
            'InstanceId': instance_id
        }
    )
    dynamo_items = dynamo_response['Item']
    # 인스턴스 ID를 사용해 인스턴스 타입, CPU size, MEM size, GPU 여부에 대한 정보를 가져옴
    instance_info = ec2_client.describe_instances(
        InstanceId=[instance_id,]
    )
    instance_type = instance_info['Reservations']['Instances']['InstanceType']
    architecture = instance_info['Reservations']['Instances']['Architecture']
    instance_cpu = instance_info['Reservations']['Instances']['CpuOptions']['CoreCount']
    instance_type_info = ec2_client.describe_instance_types(
        InstanceTypes=[
            instance_type,
        ]
    )
    instance_mem = instance_type_info['InstanceTypes']['MemoryInfo']['SizeInMiB']
    ## 인터럽트에 의한 마이그레이션의 경우
    instance_type_to_migrate = None
    if migration_type == 'interrupted':
    ### 현재 인스턴스 타입과 같은 하드웨어 size인 최적의 인스턴스를 선택함
        instance_type_to_migrate = selectInstance(instance_cpu, instance_mem)
    ## CPU/MEM Usage High/Low에 의한 마이그레이션의 경우
    elif migration_type == 'cpuHigh':
        instance_type_to_migrate = selectInstance(instance_cpu*2, instance_mem)
    ### 변경된 하드웨어 size인 최적의 인스턴스를 선택함
    elif migration_type == 'cpuLow':
        instance_type_to_migrate = selectInstance(instance_cpu//2, instance_mem)
    elif migration_type == 'memHigh':
        instance_type_to_migrate = selectInstance(instance_cpu, instance_mem*2)
    elif migration_type == 'memLow':
        instance_type_to_migrate = selectInstance(instance_cpu, instance_mem//2)
    # 선택한 인스턴스 타입을 프로비저닝하고, 마이그레이션을 위한 환경 구성을 Userdata를 통해 구성
    # SSM의 send_command를 사용해 세부 마이그레이션 작업 완료
    # 현재 가동중인 인스턴스 정보를 저장하는 db에서 인스턴스 구성 설정을 가져옴(port 설정, Userdata 등)
    # 웹페이지를 지원한다면 ALB에 연결된 target group의 인스턴스를 기존 인스턴스에서 새로운 인스턴스로 교체
    # 기존 인스턴스를 terminate
    return {
        "statusCode": 200,
        "message": "Migration Complete"
    }