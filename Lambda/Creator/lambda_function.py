import boto3
import base64
from tools import selectInstance
from variables import *

ec2_client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
iam_client = boto3.client('iam')
dynamodb = boto3.resource('dynamodb')

table = dynamodb.Table(f'{prefix}DynamoDB')

def lambda_handler(event, context):
    # API를 통해 생성하고자 하는 인스턴스 정보를 얻어옴 (Name, Userdata, Port, Security, hardware size 등)
    instance_name = event["queryStringParameters"]['InstanceName']
    username = event["queryStringParameters"]['UserName']
    userdata = event["queryStringParameters"]['Userdata']
    docker_image = event["queryStringParameters"]['DockerImage']
    ports = event["queryStringParameters"]['Ports']
    ssh_support = event["queryStringParameters"]['SupportSSH']
    web_support = event["queryStringParameters"]['SupportWebService']
    # hardware size를 통해 최적의 인스턴스를 선택
    instance_type, az = None, None
    if 'InstanceType' in event["queryStringParameters"]:
        instance_type = event["queryStringParameters"]['InstanceType']
        instance_type, az = selectInstance(InstanceType=instance_type)
    else:
        instance_type, az = selectInstance(vCPU=event['queryStringParameters']['vCPU'], MEM=event['queryStringParameters']['Mem'], GPU=event['queryStringParameters'].get('GPU', None))
    # Name, Userdata, Security 정보를 사용해 인스턴스를 프로비저닝
    init_userdata_arm = f"""#!/bin/bash
sudo yum update -y
sudo yum upgrade -y
sudo yum install podman -y
sudo podman pull {docker_image}
sudo dnf install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_arm64/amazon-ssm-agent.rpm
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
sudo yum -y install git
git clone https://github.com/aws/efs-utils
sudo yum -y install make
sudo yum install rpm-build
sudo make -C efs-utils/ rpm
sudo yum -y install efs-utils/build/amazon-efs-utils*rpm
sudo mkdir {EFS_PATH}
sudo mount -t efs -o tls {EFS_ID}:/ {EFS_PATH}
sudo podman run --name {instance_name} -e GRANT_SUDO=yes --user root {[f"-p {port}" for port in ports].join(" ")} -d {docker_image} {userdata}
"""
    init_userdata_x86_64 = f"""#!/bin/bash
sudo yum update -y
sudo yum upgrade -y
sudo yum install podman -y
sudo podman pull {docker_image}
sudo dnf install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
sudo yum -y install git
git clone https://github.com/aws/efs-utils
sudo yum -y install make
sudo yum install rpm-build
sudo make -C efs-utils/ rpm
sudo yum -y install efs-utils/build/amazon-efs-utils*rpm
sudo mkdir {EFS_PATH}
sudo mount -t efs -o tls {EFS_ID}:/ {EFS_PATH}
sudo podman run --name {instance_name} -e GRANT_SUDO=yes --user root {[f"-p {port}" for port in ports].join(" ")} -d {docker_image} {userdata}
"""
    # 인스턴스 생성을 위해 vpc, subnet id 검색
    vpc_id = ec2_client.describe_vpcs(
        Filters=[
            {'Name': 'tag:Name', 'Values': [f"{prefix}-vpc"]}
        ]
    )['Vpcs'][0]['VpcId']
    subnet_id = ec2_client.describe_subnets(
        Filters=[
            {'Name': 'vpc-id', 'Values': [vpc_id]},
            {'Name': 'availability-zone', 'Values': [az]}
        ]
    )['Subnets'][0]['SubnetId']
    # security group 생성
    security_group = ec2.create_security_group(
        GroupName=f"{instance_name}-sg",
        Description=f"security group of {instance_name} in {prefix} system.",
        VpcId=vpc_id
    )
    for port in ports:
        ingress = port.split(":")[0]
        security_group.authorize_ingress(
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': int(ingress),
                    'ToPort': int(ingress),
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
    if ssh_support == True:
        security_group.authorize_ingress(
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
    # iam 탐색
    spot_iam_role_arn = iam_client.get_role(RoleName=f"{prefix}-spot-instance-role")['Role']['Arn']
    response = ec2_client.request_spot_instances(
        InstanceCount=1,
        LaunchSpecification={
            'ImageId': init_userdata_x86_64,
            'InstanceType': instance_type,
            'Placement': {'AvailabilityZone': az},
            'SubnetId': subnet_id,
            'SecurityGroupIds': [security_group['GroupId']],
            'IamInstanceProfile': {
                'Arn': spot_iam_role_arn
            },
            'UserData': base64.b64encode(init_userdata_arm.encode('utf-8')).decode('utf-8')
        }
    )
    # 생성된 인스턴스를 인스턴스 관리 DB에 기록
    item = {
        'InstanceId': '',
        'InstanceName': instance_name,
        'InstanceType': instance_type,
        'AvailabilityZone': az,
        'Status': 'running',
        'UserName': username,
        'UserData': '',
        'SupportSSH': '',
        'SupportWebService': ''
    }
    response = table.put_item(Item=item)
    # 생성된 인스턴스의 CPU, MEM Usage를 체크하는 EventBridge Alarm, Rule을 생성 후 Migrator에 연결
    # 웹페이지를 지원한다면 ALB에 연결
    return {
        "statusCode": 200,
        "message": "Migration Complete"
    }