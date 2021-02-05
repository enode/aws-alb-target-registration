import os
from datetime import datetime
from botocore.exceptions import ClientError
import boto3

'''
Configure these environment variables in your Lambda environment (CloudFormation Inputs)
1. ALB_NAME - The name of the Application Load Balancer (format app//)
2. ALB_LISTENER - The traffic listener port of the Application Load Balancer
3. NLB_TG_ARN - The ARN of the Network Load Balancer's target group
4. CW_METRIC_FLAG_IP_COUNT - The controller flag that enables CloudWatch metric of IP count
'''


ALB_NAME = os.environ['ALB_NAME']
ALB_LISTENER = int(os.environ['ALB_LISTENER'])
NLB_TG_ARN = os.environ['NLB_TG_ARN']
CW_METRIC_FLAG_IP_COUNT  = os.environ['CW_METRIC_FLAG_IP_COUNT']


TIME = datetime.strftime(((datetime.utcnow())), '%Y-%m-%d %H:%M:%S')

try:
    cwclient = boto3.client('cloudwatch')
except ClientError as e:
    print e.response['Error']['Message']
    sys.exit(1)
try:
    elbv2client = boto3.client('elbv2')
except ClientError as e:
    print e.response['Error']['Message']
    sys.exit(1)
try:
    ec2client = boto3.client('ec2')
except ClientError as e:
    print e.response['Error']['Message']
    sys.exit(1)

def put_metric_data(ip_dict):
    """
    Put metric -- IPCount to CloudWatch
    """
    try:
        cwclient.put_metric_data(
            Namespace='AWS/ApplicationELB',
            MetricData=[
                {
                    'MetricName': "LoadBalancerIPCount",
                    'Dimensions': [
                        {
                            'Name': 'LoadBalancerName',
                            'Value': ip_dict['LoadBalancerName']
                        },
                    ],
                    'Value': float(ip_dict['IPCount']),
                    'Unit': 'Count'
                },
            ]
        )
    except ClientError as e:
        print e
		

def register_target(tg_arn, new_target_list):
    """
      Register ALB's IP to NLB's target group
    """
    print "INFO: Register new_target_list:{}".format(new_target_list)
    try:
        elbv2client.register_targets(
            TargetGroupArn=tg_arn,
            Targets=new_target_list
        )
    except ClientError as e:
        print e


def deregister_target(tg_arn, new_target_list):
    """
      Deregister ALB's IP from NLB's target group
    """
    try:
        print "INFO: Deregistering targets: {}".format(new_target_list)
        elbv2client.deregister_targets(
            TargetGroupArn=tg_arn,
            Targets=new_target_list
        )
    except ClientError as e:
        print e


def target_group_list(ip_list):
    """
          Render a list of targets for registration
    """
    target_list = []
    for ip in ip_list:
        target = {
            'Id': ip,
            'Port': ALB_LISTENER,
        }
        target_list.append(target)
    return target_list


def describe_target_health(tg_arn):
    """
      Get a IP address list of registered targets in the NLB's target group
    """
    registered_ip_list = []
    try:
        response = elbv2client.describe_target_health(
            TargetGroupArn=tg_arn)
        registered_ip_count = len(response['TargetHealthDescriptions'])
        print "INFO: Number of currently registered IP: ", registered_ip_count
        for target in response['TargetHealthDescriptions']:
            registered_ip = target['Target']['Id']
            registered_ip_list.append(registered_ip)
    except ClientError as e:
        print e
    return registered_ip_list


def lambda_handler(event, context):
    """
        Main Lambda handler
        This is invoked when Lambda is called
        """
		
    registered_ip_list = describe_target_health(NLB_TG_ARN)
   
    networks_response = ec2client.describe_network_interfaces(
        Filters=[
            {
                'Name': 'description',
                'Values': [
                    'ELB ' + ALB_NAME,
                ]
            },
        ],
        DryRun=False
    )

    ip_list = list()
    for network in networks_response["NetworkInterfaces"]:
        for address in network["PrivateIpAddresses"]:
            ip_list.append(address["PrivateIpAddress"])
    
    new_active_ip_dict = {"LoadBalancerName": ALB_NAME, "TimeStamp": TIME}
    new_active_ip_dict["IPList"] = ip_list
    new_active_ip_dict["IPCount"] = len(ip_list)
    if CW_METRIC_FLAG_IP_COUNT.lower() == "true":
        put_metric_data(new_active_ip_dict)

    #construct set of new active IPs and registered IPs
    new_active_ip_set = set(new_active_ip_dict['IPList'])
    registered_ip_set = set(registered_ip_list)

    # Check for Registration
    # IPs that have not been registered, and missing from the old active IP list
    registration_ip_list = list(new_active_ip_set - registered_ip_set)
    
    # Check for Deregistration
    deregiter_ip_diff_set = list(registered_ip_set - new_active_ip_set)
    print "INFO: Pending deregistration IPs from current invocation - {}".\
        format(deregiter_ip_diff_set)

    if registration_ip_list:
        registerTarget_list = target_group_list(registration_ip_list)
        register_target(NLB_TG_ARN, registerTarget_list)
        print "INFO: Registering {}".format(registration_ip_list)

    else:
        print "INFO: No new target registered"

    if deregiter_ip_diff_set:
        deregisterTarget_list = target_group_list(deregiter_ip_diff_set)
        deregister_target(NLB_TG_ARN, deregisterTarget_list)
    else:
        print "INFO: No old target deregistered"
