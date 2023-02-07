from aws_cdk import (
    Stack,
    aws_iam as _iam,
)
from constructs import Construct

def create_policy_s3(self, region, account_id):
    return  _iam.PolicyStatement(
            actions=["s3:*"],
            resources=["*"]
        )

def create_policy_passrole_rekognition(self, region, account_id):
    return  _iam.PolicyStatement(
            actions=["iam:PassRole"],
            resources=["*"],
            conditions={
                "StringEquals": {
                    "iam:PassedToService": "rekognition.amazonaws.com"
                }
            }
        )
        
def create_policy_rekognition(self, region, account_id):
    return  _iam.PolicyStatement(
            actions=["rekognition:DetectModerationLabels"],
            resources=["*"]
        )

def create_policy_sns(self, region, account_id):
    return  _iam.PolicyStatement(
            actions=["sns:Publish"],
            resources=["*"]
        )


def create_policy_lambda_log(self, region, account_id):
    return  _iam.PolicyStatement(
            actions=["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
            resources=[f"arn:aws:logs:{region}:{account_id}:*"]
        )