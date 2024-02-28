import boto3
import time

ssm_client = boto3.client('ssm')
ec2_client = boto3.client('ec2')

def selectInstance(InstanceType=None, vCPU=None, MEM=None, GPU=None):
    if InstanceType != None:
        return (InstanceType, 'us-west-1a')
    else:
        CPU_MIN = vCPU.split("-")[0]
        CPU_MAX = vCPU.split("-")[1]
        MEM_MIN = MEM.split("-")[0]
        MEM_MAX = MEM.split("-")[1]
        if GPU != None:
            GPU_MIN = GPU.split("-")[0]
            GPU_MAX = GPU.split("-")[1]
        return ('t3.small', 'us-west-1a')

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
