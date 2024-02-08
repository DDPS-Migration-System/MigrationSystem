import boto3
import json

ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    # 조작의 대상 인스턴스 ID, 어떤 조작(Stop, Start, Terminate)을 가할것인지에 대한 정보를 가져옴
    control_type = event["queryStringParameters"]["ControlType"]
    instance_id = event["queryStringParameters"]["InstanceId"]
    # 조작 수행
    response = None
    if control_type == 'start':
        response = ec2_client.start_instances(InstanceIds=[instance_id])
    elif control_type == 'stop':
        response = ec2_client.stop_instances(InstanceIds=[instance_id])
    elif control_type == 'terminate':
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])
    print(response)
    return {
        "statusCode": 200,
        "message": json.dumps(response)
    }