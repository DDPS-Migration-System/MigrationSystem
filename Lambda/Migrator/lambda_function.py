import boto3
import json
import base64
from tools import selectInstance, waiter_send_message
from variables import *

ec2_client = boto3.client('ec2')
dynamodb = boto3.resource('dynamodb')
elbv2_client = boto3.client('elbv2')

table = dynamodb.Table(f'{prefix}DynamoDB')

def lambda_handler(event, context):
    # 마이그레이션 종류 얻어옴
    migration_type = event["queryStringParameters"]["migrationType"]
    # 인터럽트가 발생한 인스턴스의 ID 얻어옴
    instance_id = event["queryStringParameters"]["instanceId"]
    # 현재 가동중인 인스턴스 정보를 저장하는 db에서 인스턴스 구성 설정을 가져옴(Userdata)
    dynamo_response = table.get_item(
        Key={
            'InstanceId': instance_id
        }
    )
    dynamo_items = dynamo_response['Item']
    # 인스턴스 ID를 사용해 인스턴스 타입, CPU size, MEM size, GPU 여부, Subnet ID, SecurityGroup ID, IAM Profile에 대한 정보를 가져옴
    instance_info = ec2_client.describe_instances(
        InstanceId=[instance_id,]
    )
    instance_type = instance_info['Reservations'][0]['Instances'][0]['InstanceType']
    architecture = instance_info['Reservations'][0]['Instances'][0]['Architecture']
    instance_cpu = instance_info['Reservations'][0]['Instances'][0]['CpuOptions']['CoreCount']
    instance_type_info = ec2_client.describe_instance_types(
        InstanceTypes=[
            instance_type,
        ]
    )
    instance_mem = instance_type_info['InstanceTypes']['MemoryInfo']['SizeInMiB']
    subnet_id = instance_info['Reservations'][0]['Instances'][0]['SubnetId']
    sg_ids = [sg['GroupId'] for sg in instance_info['Reservations'][0]['Instances'][0]['SecurityGroups']]
    spot_iam_role_arn = instance_info['Reservations'][0]['Instances'][0]['IamInstanceProfile']['Arn']
    ## 인터럽트에 의한 마이그레이션의 경우
    instance_type_to_migrate = None
    if migration_type == 'interrupted':
    ### 현재 인스턴스 타입과 같은 하드웨어 size인 최적의 인스턴스를 선택함
        instance_type_to_migrate = selectInstance(InstanceType=instance_type, vCPU=instance_cpu, MEM=instance_mem)
    ## CPU/MEM Usage High/Low에 의한 마이그레이션의 경우
    elif migration_type == 'cpuHigh':
        instance_type_to_migrate, az_to_migrate = selectInstance(InstanceType=instance_type, vCPU=instance_cpu*2, MEM=instance_mem)
    ### 변경된 하드웨어 size인 최적의 인스턴스를 선택함
    elif migration_type == 'cpuLow':
        instance_type_to_migrate, az_to_migrate = selectInstance(InstanceType=instance_type, vCPU=instance_cpu//2, MEM=instance_mem)
    elif migration_type == 'memHigh':
        instance_type_to_migrate, az_to_migrate = selectInstance(InstanceType=instance_type, vCPU=instance_cpu, MEM=instance_mem*2)
    elif migration_type == 'memLow':
        instance_type_to_migrate, az_to_migrate = selectInstance(InstanceType=instance_type, vCPU=instance_cpu, MEM=instance_mem//2)
    # 선택한 인스턴스 타입을 프로비저닝하고, 마이그레이션을 위한 환경 구성을 Userdata를 통해 구성
    response = ec2_client.request_spot_instances(
        InstanceCount=1,
        LaunchSpecification={
            'ImageId': architecture,
            'InstanceType': instance_type_to_migrate,
            'Placement': {'AvailabilityZone': az_to_migrate},
            'SubnetId': subnet_id,
            'SecurityGroupIds': sg_ids,
            'IamInstanceProfile': {
                'Arn': spot_iam_role_arn
            },
            'UserData': base64.b64encode(dynamo_items['UserData'].encode('utf-8')).decode('utf-8')
        }
    )
    # SSM의 send_command를 사용해 세부 마이그레이션 작업 완료
    # 체크포인트 작업
    # 추후 EFS(혹은 EBS)를 기본 podman의 root directory로 설정하여 gz 파일 추출 과정을 제거하도록 진행 예정
    command = f'sudo podman container checkpoint {dynamo_items["InstanceName"]} --file-locks --tcp-established --keep --print-stats -e {EFS_PATH}/{dynamo_items["InstanceName"]}_checkpoint.tar.gz'
    waiter_send_message(instance_id, command)
    command = f"sudo podman container restore --file-locks --tcp-established --keep --print-stats --import {EFS_PATH}/{dynamo_items['InstanceName']}_checkpoint.tar.gz"
    waiter_send_message(response['SpotInstanceRequests'][0]['InstanceId'], command)
    # 웹페이지를 지원한다면 ALB에 연결된 target group의 인스턴스를 기존 인스턴스에서 새로운 인스턴스로 교체
    if dynamo_items['SupportWebService'] != False:
        albs = elbv2_client.describe_load_balancers(Names=[f'{prefix}-alb'])
        alb_arn = albs['LoadBalancers'][0]['LoadBalancerArn']
        listeners = elbv2_client.describe_listeners(LoadBalancerArn=alb_arn)
        for listener in listeners['Listeners']:
            rules = elbv2_client.describe_rules(ListenerArn=listener['ListenerArn'])
            for rule in rules['Rules']:
                for action in rule['Actions']:
                    if action['Type'] == 'forward':
                        for condition in rule['Conditions']:
                            if condition['Field'] == 'path-pattern' and f'/{dynamo_items["InstanceName"]}' in condition['Values']:
                                target_group_arn = action['TargetGroupArn']
        elbv2_client.deregister_targets(
            TargetGroupArn=target_group_arn,
            Targets={"Id": instance_id}
        )
        elbv2_client.register_targets(
            TargetGroupArn=target_group_arn,
            Targets={"Id": response['SpotInstanceRequests'][0]['InstanceId']}
        )
    # 기존 인스턴스를 terminate
    response = ec2_client.terminate_instances(InstanceIds=[instance_id])
    return {
        "statusCode": 200,
        "message": "Migration Complete"
    }