import boto3
import time
import base64
import hmac
from botocore.exceptions import ClientError

ssm_client = boto3.client('ssm')
ec2_client = boto3.client('ec2')

def selectInstance(InstanceType=None, vCPU=None, MEM=None, GPU=None):
    if InstanceType != None:
        return (InstanceType, 'us-west-2a')
    else:
        CPU_MIN = vCPU.split("-")[0]
        CPU_MAX = vCPU.split("-")[1]
        MEM_MIN = MEM.split("-")[0]
        MEM_MAX = MEM.split("-")[1]
        if GPU != None:
            GPU_MIN = GPU.split("-")[0]
            GPU_MAX = GPU.split("-")[1]
        return ('t3.small', 'us-west-2a')

def waiter_send_message(instanceId, command):
    response = ssm_client.send_command(
        InstanceIds=[instanceId,],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands':[command]}
    )
    commandId = response['Command']['CommandId']
    while True:
        try:
            command_invocation = ssm_client.get_command_invocation(
                CommandId=commandId,
                InstanceId=instanceId,
            )
            status = command_invocation['Status']
            if status == 'Success':
                break
            elif status == 'Failed':
                print("[ERROR] Run Command Failed")
                exit()
        except Exception as e:
            time.sleep(1)

def waiter_userdata_complete(instanceId, state, mst):
    command = 'sudo tail -n 1 /var/log/cloud-init-output.log | grep finished | wc -l'
    while state == "INIT" or (state=="MIGRATE" and time.time() - mst < 90):
        try:
            response = ssm_client.send_command(
                InstanceIds=[instanceId],
                DocumentName='AWS-RunShellScript',
                Parameters={'commands': [command]}
            )
            commandId = response['Command']['CommandId']

            time.sleep(1)

            output_response = ssm_client.get_command_invocation(
                CommandId=commandId,
                InstanceId=instanceId,
            )
            if output_response['StandardOutputContent'].strip() == '1':
                return True
        except Exception as e:
            time.sleep(1)
    return False

def get_rhel9_ami_id(architecture):    
    # Red Hat Enterprise Linux 9 (HVM) AMI를 검색
    response = ec2_client.describe_images(
        Filters=[
                {'Name': 'name', 'Values': ['RHEL-9.0*_HVM-*']},
                {'Name': 'architecture', 'Values': [architecture]},
                {'Name': 'owner-alias', 'Values': ['amazon']}
            ]
    )
    
    # AMI ID를 반환
    images = response.get('Images', [])

    # 최신 AMI를 선택하기 위해 정렬
    sorted_images = sorted(images, key=lambda x: x['CreationDate'], reverse=True)
    ami_id = sorted_images[0]['ImageId']

    return ami_id

def get_supported_architecture(instance_type):    
    # 인스턴스 유형의 상세 정보를 가져오기
    response = ec2_client.describe_instance_types(
        InstanceTypes=[instance_type]
    )
    
    # 인스턴스 유형의 지원 아키텍처를 반환
    instance_info = response['InstanceTypes'][0]
    supported_architectures = instance_info['ProcessorInfo']['SupportedArchitectures']
    
    # x86과 ARM 중 모두 지원한다면 x86을 반환
    if 'x86_64' in supported_architectures:
        return 'x86_64'
    else:
        return 'arm64'

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

def get_secret_hash(username, client_id):
    client_secret = get_ssm_parameter('stablespot-user-pool-client-secret')
    message = username + client_id
    dig = hmac.new(client_secret.encode('UTF-8'), msg=message.encode('UTF-8'), digestmod=hashlib.sha256).digest()
    d2 = base64.b64encode(dig).decode()
    return d2
