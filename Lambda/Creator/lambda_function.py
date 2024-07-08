import boto3
import base64
import json
import time
from tools import selectInstance
from tools import get_rhel9_ami_id
from tools import get_supported_architecture
from tools import get_ssm_parameter
from variables import *

ec2_client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
iam_client = boto3.client('iam')
ssm_client = boto3.client('ssm')
cognito_client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')
elbv2_client = boto3.client('elbv2')

table = dynamodb.Table(f'{prefix}DynamoDB')
EFS_ID = get_ssm_parameter(f'{prefix}-efs-id')
EFS_PATH = "EFS"
user_pools = cognito_client.list_user_pools(MaxResults=60)

cloudwatch_config = """
{
  "agent": {
    "metrics_collection_interval": 60,
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "metrics": {
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}"
    },
    "metrics_collected": {
      "cpu": {
        "measurement": [
          "cpu_usage_idle",
          "cpu_usage_user",
          "cpu_usage_system"
        ],
        "metrics_collection_interval": 60,
        "totalcpu": true
      },
      "mem": {
        "measurement": [
          "mem_used_percent"
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
"""

def lambda_handler(event, context):
    # API를 통해 생성하고자 하는 인스턴스 정보를 얻어옴 (Name, Userdata, Port, Security, hardware size 등)
    body = json.loads(event['body'])  # 요청 본문을 JSON으로 파싱
    instance_name = body['InstanceName']  # 인스턴스 이름
    username = body['UserName']  # 사용자 이름
    userdata = body.get('UserData', "")
    docker_image = body['DockerImage']  # 도커 이미지
    ports = body['Ports'].split(",")  # 포트들, 쉼표로 구분된 문자열을 리스트로 변환
    ssh_support = body['SupportSSH']  # SSH 지원 여부
    web_support = body.get('SupportWebService','') # 웹 서비스 지원 여부
    
    # 하드웨어 사이즈를 기반으로 최적의 인스턴스 선택
    instance_type, az = None, None
    if 'InstanceType' in body:
        instance_type = body['InstanceType']  # 인스턴스 유형 지정
        instance_type, az = selectInstance(InstanceType=instance_type)  # 인스턴스 유형과 가용 구역 선택
    else:
        # vCPU, 메모리, GPU를 기준으로 인스턴스 유형과 가용 구역 선택
        instance_type, az = selectInstance(vCPU=body['vCPU'], MEM=body['Mem'], GPU=body.get('GPU', None))
    isWeb = "false"
    web_support_port = ""
    if web_support:
        web_support_cp = body.get('SupportWebService','').split(",")
        web_support_port = " ".join([f"-p {port}" for port in web_support_cp])
        isWeb = "true"

    
    print(web_support_port)
    
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
sudo yum install rpm-build -y
sudo yum install -y openssl-devel
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
export PATH="$HOME/.cargo/bin:$PATH"
rustup default stable
echo 'source $HOME/.cargo/env' >> ~/.bashrc
source ~/.bashrc
sudo sed -i '/%build/a export PATH=/home/ec2-user/.cargo/bin:$PATH\nrustup default stable' /efs-utils/amazon-efs-utils.spec
sudo yum groupinstall -y "Development Tools"
sudo yum install -y gcc gcc-c++ make
sudo make -C efs-utils/ rpm
sudo yum -y install efs-utils/build/amazon-efs-utils*rpm
sudo mkdir {EFS_PATH}
sudo mount -t efs -o tls {EFS_ID}:/ {EFS_PATH}
sudo podman run --name {instance_name} -e GRANT_SUDO=yes --user root {" ".join([f"-p {port}" for port in ports])} {web_support_port} -d {docker_image} {userdata}
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
sudo yum install rpm-build -y
sudo yum install -y openssl-devel
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
export PATH="$HOME/.cargo/bin:$PATH"
rustup default stable
echo 'source $HOME/.cargo/env' >> ~/.bashrc
source ~/.bashrc
sudo sed -i '/%build/a export PATH=/home/ec2-user/.cargo/bin:$PATH\nrustup default stable' /efs-utils/amazon-efs-utils.spec
sudo yum groupinstall -y "Development Tools"
sudo yum install -y gcc gcc-c++ make
sudo make -C efs-utils/ rpm
sudo yum -y install efs-utils/build/amazon-efs-utils*rpm
sudo mkdir {EFS_PATH}
sudo mount -t efs -o tls {EFS_ID}:/ {EFS_PATH}
sudo podman run --name {instance_name} -e GRANT_SUDO=yes --user root {" ".join([f"-p {port}" for port in ports])} {web_support_port} -d {docker_image} {userdata}
"""
    # 인스턴스 생성을 위해 vpc, subnet id 검색
    print(prefix)
    try:
        # VPC ID 가져오기
        vpcs = ec2_client.describe_vpcs(
            Filters=[
                {'Name': 'tag:Name', 'Values': [f"{prefix}-vpc"]}
            ]
        )['Vpcs']
        
        if not vpcs:
            raise ValueError(f"태그 이름이 '{prefix}-vpc'인 VPC를 찾을 수 없습니다.")
        
        vpc_id = vpcs[0]['VpcId']
        
        # 서브넷 ID 가져오기
        subnets = ec2_client.describe_subnets(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'availability-zone', 'Values': [az]},
            ]
        )['Subnets']
        
        if not subnets:
            raise ValueError(f"VPC ID가 '{vpc_id}'이고 가용 영역이 '{az}'인 서브넷을 찾을 수 없습니다.")
        
        public_subnet = None
        for subnet in subnets:
            if 'Tags' in subnet:
                for tag in subnet['Tags']:
                    if tag['Key'] == 'Name' and tag['Value'].startswith(f"{prefix}-public"):
                        public_subnet = subnet
                        break
            if public_subnet:
                break
        
        if not public_subnet:
            raise ValueError(f"VPC ID가 '{vpc_id}'이고 가용 영역이 '{az}'이며 태그가 '{prefix}-public-숫자'인 서브넷을 찾을 수 없습니다.")
        
        subnet_id = public_subnet['SubnetId']

        
        print(f"VPC ID: {vpc_id}, Subnet ID: {subnet_id}")
    
    except Exception as e:
        print(f"오류 발생: {e}")
    # security group 생성
    security_group = ec2.create_security_group(
        GroupName=f"{instance_name}-sg",
        Description=f"security group of {instance_name} in {prefix} system.",
        VpcId=vpc_id
    )
    security_group_id = security_group.id
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
    if web_support != False:
        from_port, to_port = map(int, web_support.split(':'))
    if from_port > 0 and to_port > 0:
        security_group.authorize_ingress(
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': from_port,
                    'ToPort': to_port,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
    # iam 탐색
    # spot_iam_role_arn = iam_client.get_role(RoleName=f"{prefix}-spot-instance-role")['Role']['Arn']
    instance_profile_name = f"{prefix}-spot-instance-profile"
    instance_profile_response = iam_client.get_instance_profile(
        InstanceProfileName=instance_profile_name
    )
    instance_profile_arn = instance_profile_response['InstanceProfile']['Arn']

    arch = get_supported_architecture(instance_type)
    print(arch)
    image_Id = get_rhel9_ami_id(arch)
    print(image_Id)
    
    if arch == 'x86_64':
        userdata_arch = init_userdata_x86_64
    else:
        userdata_arch = init_userdata_arm

    # UserData를 base64로 인코딩
    encoded_userdata = base64.b64encode(userdata_arch.encode('utf-8')).decode('utf-8')
    
    response = ec2_client.request_spot_instances(
        InstanceCount=1,
        Type='persistent',
        LaunchSpecification={
            'ImageId': image_Id,
            'InstanceType': instance_type,
            'KeyName': 'jihun-oregon',
            'Placement': {'AvailabilityZone': az},
            'IamInstanceProfile': {
                'Arn': instance_profile_arn
            },
            'UserData': encoded_userdata,
            'NetworkInterfaces': [{
                'DeviceIndex': 0,
                'SubnetId': subnet_id,
                'AssociatePublicIpAddress': True,
                'Groups': [security_group_id]
            }]
        }
    )
    
    time.sleep(1)
    
    # Spot Instance 요청 ID 가져오기
    spot_request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    
    # Spot Instance 요청 상태 모니터링
    instance_id = None
    while instance_id is None:
        describe_response = ec2_client.describe_spot_instance_requests(
            SpotInstanceRequestIds=[spot_request_id]
        )
        request_status = describe_response['SpotInstanceRequests'][0]['Status']['Code']
        
        if request_status == 'fulfilled':
            instance_id = describe_response['SpotInstanceRequests'][0].get('InstanceId', None)
        elif 'cancelled' in request_status or 'failed' in request_status:
            raise Exception(f"Spot Instance request failed or was cancelled: {request_status}")
        
        time.sleep(1)
    
    ec2_client.create_tags(
        Resources=[instance_id],
        Tags=[
            {'Key': 'StableSpot', 'Value': prefix},
            {'Key': 'Name', 'Value': instance_name}
        ]
    )

    
    ip_address = None
    while ip_address is None:
        instance_response = ec2_client.describe_instances(
            InstanceIds=[instance_id]
        )
        reservations = instance_response['Reservations']
        if reservations:
            instances = reservations[0]['Instances']
            if instances:
                ip_address = instances[0].get('PublicIpAddress', None)
        
        time.sleep(1)

    port_number = web_support.split(":")[0]
    # 생성된 인스턴스를 인스턴스 관리 DB에 기록
    item = {
        'InstanceId': instance_id,
        'InstanceName': instance_name,
        'InstanceType': instance_type,
        'AvailabilityZone': az,
        'isRunning': 'Running',
        'UserName': username,
        'DockerImage': docker_image,
        'SupportSSH': ssh_support,
        'port': port_number,
        'IpAddress': ip_address,
        'isWeb': isWeb,
        'SpotReqId': spot_request_id
    }
    
    response = table.put_item(Item=item)
    # 생성된 인스턴스의 CPU, MEM Usage를 체크하는 EventBridge Alarm, Rule을 생성 후 Migrator에 연결
    if web_support:
        user_pool_id = get_ssm_parameter(f'{prefix}-user-pool-id')
        user_pool_client_id = get_ssm_parameter(f'{prefix}-user-pool-client-id')
        user_pool_arn = None
        user_pool_domain = None
        if user_pool_id:
            cognito_response = cognito_client.describe_user_pool(UserPoolId=user_pool_id)
            user_pool_arn = cognito_response['UserPool']['Arn']
            if 'Domain' in cognito_response['UserPool']:
                user_pool_domain = cognito_response['UserPool']['Domain']
        albs = elbv2_client.describe_load_balancers(Names=[f'{prefix}-alb'])
        alb_arn = albs['LoadBalancers'][0]['LoadBalancerArn']
        certificate_arn = get_ssm_parameter(f"{prefix}-aws_acm_certificate")
        # ALB에 리스너 생성 (예: HTTP 80 포트 리스너)
        listener_response = elbv2_client.create_listener(
            LoadBalancerArn=alb_arn,
            Protocol='HTTPS',
            Port=443,
            DefaultActions=[
                {
                'Type': 'fixed-response',
                'FixedResponseConfig': 
                    {
                    'StatusCode': '200',
                    'ContentType': 'text/plain',
                    'MessageBody': 'Default response'
                    }
                }
            ],
            Certificates=[
                    {
                        'CertificateArn': certificate_arn
                    }
                ]
        )

        listener_arn = listener_response['Listeners'][0]['ListenerArn']
        # 타겟 그룹 생성
        tg_response = elbv2_client.create_target_group(
            Name=f'{instance_name}-tg',
            Protocol='HTTP',
            Port=from_port,
            VpcId=vpc_id,
            HealthCheckProtocol='HTTP',
            HealthCheckPath='/',
            HealthCheckEnabled=True,
            TargetType='instance'
        )

        target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
        existing_rules = elbv2_client.describe_rules(ListenerArn=listener_arn)
        existing_priorities = [int(rule['Priority']) for rule in existing_rules['Rules'] if rule['Priority'].isdigit()]
        new_priority = max(existing_priorities) + 1 if existing_priorities else 1

        # 리스너 규칙 추가
        elbv2_client.create_rule(
            ListenerArn=listener_arn,
            Conditions=[{
                'Field': 'path-pattern',
                'Values': [f'/{instance_name}']
            }],
            Priority=new_priority,  # 적절한 우선순위 설정
            Actions=[{
                'Type': 'authenticate-cognito',
                'Order': 1,
                'AuthenticateCognitoConfig': {
                    'UserPoolArn': user_pool_arn,
                    'UserPoolClientId': user_pool_client_id,
                    'UserPoolDomain': user_pool_domain,  # Cognito User Pool 도메인
                    'SessionTimeout': 3600,
                    'Scope': 'openid',
                    'OnUnauthenticatedRequest': 'authenticate'
                }
            },
            {
                'Type': 'forward',
                'Order': 2,
                'TargetGroupArn': target_group_arn
            }]
        )
        
        count = 0
        while count < 120:  # 수정된 부분: 조건문 수정
            response = ec2_client.describe_instances(InstanceIds=[instance_id])
            state = response['Reservations'][0]['Instances'][0]['State']['Name']
            if state == 'running':
                # 인스턴스 등록
                elbv2_client.register_targets(
                    TargetGroupArn=target_group_arn,
                    Targets=[{'Id': instance_id}]
                )
                break
            else:
                time.sleep(5)  # 수정된 부분: 타이머와 카운트 증가
                count += 1

        if count >= 120:  # 수정된 부분: 예외 처리 추가
            return{
                "statusCode": 400,
                "message": "Invalid Error."
            }
                
    return {
        "statusCode": 200,
        "message": "Server create."
    }    