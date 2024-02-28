import boto3
import json
from variables import *

ec2_client = boto3.client('ec2')
dynamodb = boto3.resource('dynamodb')
elbv2_client = boto3.client('elbv2')

table = dynamodb.Table(f'{prefix}DynamoDB')

def lambda_handler(event, context):
    # 조작의 대상 인스턴스 ID, 어떤 조작(Stop, Start, Terminate)을 가할것인지에 대한 정보를 가져옴
    control_type = event["queryStringParameters"]["ControlType"]
    instance_id = event["queryStringParameters"]["InstanceId"]
    # 조작 수행
    response = None
    if control_type == 'start':
        response = ec2_client.start_instances(InstanceIds=[instance_id])
        responsedb = table.update_item(
            Key={
                'InstanceId': instance_id,  # 예: 'UserID': '12345'
            },
            UpdateExpression='SET #status = :newStatus',
            ExpressionAttributeNames={
                '#status': 'Status',
            },
            ExpressionAttributeValues={
                ':newStatus': 'running'
            },
            ReturnValues="UPDATED_NEW"  # 업데이트된 속성의 새로운 값 반환
        )
    elif control_type == 'stop':
        response = ec2_client.stop_instances(InstanceIds=[instance_id])
        responsedb = table.update_item(
            Key={
                'InstanceId': instance_id,  # 예: 'UserID': '12345'
            },
            UpdateExpression='SET #status = :newStatus',
            ExpressionAttributeNames={
                '#status': 'Status',
            },
            ExpressionAttributeValues={
                ':newStatus': 'stopped'
            },
            ReturnValues="UPDATED_NEW"  # 업데이트된 속성의 새로운 값 반환
        )
    elif control_type == 'terminate':# Target Group 찾기
        response = elbv2_client.describe_target_groups()
        target_groups_to_delete = []

        for tg in response['TargetGroups']:
            # 각 Target Group에 등록된 대상 확인
            targets = elbv2_client.describe_target_health(TargetGroupArn=tg['TargetGroupArn'])
            for target in targets['TargetHealthDescriptions']:
                if target['Target']['Id'] == instance_id:
                    target_groups_to_delete.append(tg['TargetGroupArn'])
                    break

        # Target Group 삭제
        for tg_arn in target_groups_to_delete:
            # 해당 Target Group을 사용하는 Listener 찾기
            listeners = elbv2_client.describe_listeners(LoadBalancerArn='YOUR_LOAD_BALANCER_ARN')
            for listener in listeners['Listeners']:
                for action in listener['DefaultActions']:
                    if action['TargetGroupArn'] == tg_arn:
                        # Listener 삭제
                        elbv2_client.delete_listener(ListenerArn=listener['ListenerArn'])
            # Target Group 삭제
            elbv2_client.delete_target_group(TargetGroupArn=tg_arn)
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])
        responsedb = table.delete_item(
            Key={
                'InstanceId': instance_id,
            }
        )
    print(response)
    print(responsedb)
    return {
        "statusCode": 200,
        "message": json.dumps(response)
    }