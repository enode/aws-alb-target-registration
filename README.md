# aws-alb-target-registration
A lambda function to automatically register the private IP-addresses of an ALB in a target group e.g. for use to set an ALB as a target for a NLB


# Configuration

Configure a access policy like:

```JSON
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData",
                "ec2:DescribeNetworkInterfaces",
                "elasticloadbalancing:DescribeTargetHealth"
            ],
            "Resource": "*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:CreateLogGroup"
            ],
            "Resource": [
                "<log arn>"
            ]
        },
        {
            "Sid": "VisualEditor2",
            "Effect": "Allow",
            "Action": [
                "elasticloadbalancing:RegisterTargets",
                "elasticloadbalancing:DeregisterTargets"
            ],
            "Resource": [
                "<Target group arn>"
            ]
        }
    ]
}
```
and assign it to the execution role of the lambda

Configure these environment variables in your Lambda environment
1. ALB_NAME - The name of the Application Load Balancer (format app/<name>/<id>)
2. ALB_LISTENER - The traffic listener port of the Application Load Balancer
3. NLB_TG_ARN - The ARN of the Network Load Balancer's target group
4. CW_METRIC_FLAG_IP_COUNT - The controller flag that enables CloudWatch metric of IP count
