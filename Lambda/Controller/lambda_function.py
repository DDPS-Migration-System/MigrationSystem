import boto3
import json
import time
from variables import *

ec2_client = boto3.client('ec2')
dynamodb = boto3.resource('dynamodb')
elbv2_client = boto3.client('elbv2')

table = dynamodb.Table(f'{prefix}DynamoDB')

def update_ip_address(instance_id):
    ip_address = None
    while ip_address is None:
        instance_response = ec2_client.describe_instances(InstanceIds=[instance_id])
        reservations = instance_response['Reservations']
        if reservations:
            instances = reservations[0]['Instances']
            if instances:
                ip_address = instances[0].get('PublicIpAddress', None)
        
        time.sleep(1)
    
    return ip_address


def lambda_handler(event, context):
    # 조작의 대상 인스턴스 ID, 어떤 조작(Stop, Start, Terminate)을 가할것인지에 대한 정보를 가져옴
    body = json.loads(event['body'])  # 요청 본문을 JSON으로 파싱
    instance_id = body['InstanceId']
    instance_name = body['InstanceName']
    control_type = body['ControllType']
    spot_request_id = body['SpotReqId']

    # 조작 수행
    response = None
    if control_type == 'start':
        response = ec2_client.start_instances(InstanceIds=[instance_id])
        
        # 실제로 인스턴스가 시작될 때까지 대기
        waiter = ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        
        # 인스턴스 시작 후 새로운 IP 주소 조회
        new_ip_address = update_ip_address(instance_id)

        responsedb = table.update_item(
            Key={
                'InstanceId': instance_id,
                'InstanceName': instance_name
            },
            UpdateExpression='SET #isRunning = :newStatus, #IpAddress = :newIpAddress',
            ExpressionAttributeNames={
                '#isRunning': 'isRunning',
                '#IpAddress': 'IpAddress'
            },
            ExpressionAttributeValues={
                ':newStatus': 'Running',
                ':newIpAddress': new_ip_address
            },
            ReturnValues="UPDATED_NEW"
        )
    elif control_type == 'stop':
        response = ec2_client.stop_instances(InstanceIds=[instance_id])
        
        waiter = ec2_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=[instance_id])

        responsedb = table.update_item(
            Key={
                'InstanceId': instance_id,  # 예: 'UserID': '12345'
                'InstanceName': instance_name
            },
            UpdateExpression='SET #isRunning = :newStatus, #IpAddress = :newIpAddress',
            ExpressionAttributeNames={
                '#isRunning': 'isRunning',
                '#IpAddress': 'IpAddress'
            },
            ExpressionAttributeValues={
                ':newStatus': 'Stopped',
                ':newIpAddress': "-"
            },
            ReturnValues="UPDATED_NEW"
        )
    elif control_type == 'terminate':# Target Group 찾기
        elbv2_client = boto3.client('elbv2')

        # 삭제할 타겟 그룹을 저장할 리스트
        target_groups_to_delete = []
        
        # 모든 타겟 그룹 조회
        response = elbv2_client.describe_target_groups()
        
        # 각 타겟 그룹에 대한 대상 확인
        for tg in response['TargetGroups']:
            targets = elbv2_client.describe_target_health(TargetGroupArn=tg['TargetGroupArn'])
            for target in targets['TargetHealthDescriptions']:
                if target['Target']['Id'] == instance_id:
                    target_groups_to_delete.append(tg['TargetGroupArn'])
                    break
        
        # 타겟 그룹 삭제
        for tg_arn in target_groups_to_delete:
            # 해당 타겟 그룹을 사용하는 리스너 찾기
            listeners_response = elbv2_client.describe_listeners(LoadBalancerArn=alb_arn)
            for listener in listeners_response['Listeners']:
                for action in listener['DefaultActions']:
                    if 'TargetGroupArn' in action and action['TargetGroupArn'] == tg_arn:
                        # 리스너 삭제
                        elbv2_client.delete_listener(ListenerArn=listener['ListenerArn'])
            
        # 타겟 그룹 삭제
        elbv2_client.delete_target_group(TargetGroupArn=tg_arn)
        

    

        # persistent 요청 중단
        response = ec2_client.cancel_spot_instance_requests(SpotInstanceRequestIds=[spot_request_id])

        
        # instance 삭제
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])
        
        # instance가 삭제 될 때까지 대기
        waiter = ec2_client.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])
        
        # Security Group 찾기
        security_groups = ec2_client.describe_security_groups(
            Filters=[
                {'Name': 'group-name', 'Values': [f'{instance_name}-sg']}
            ]
        )['SecurityGroups']
        
        for sg in security_groups:
            security_group_id = sg['GroupId']
            
            # Security Group 삭제
            ec2_client.delete_security_group(GroupId=security_group_id)
        # db 삭제
        responsedb = table.delete_item(
            Key={
                'InstanceId': instance_id,
                'InstanceName': instance_name
            }
        )
    print(response)
    print(responsedb)
    return {
        "statusCode": 200,
        "message": json.dumps(response)
    }