from aws_cdk import (
    Stack,
    aws_iam as _iam,
)
from constructs import Construct
from iam_role import policy


def create_role(self, region, account_id):
    # IAM role
    new_role = _iam.Role(self, "lambda-all-in-one",
        assumed_by=_iam.ServicePrincipal("lambda.amazonaws.com"),
    )
    new_role.add_to_policy(
        # S3 read access
        policy.create_policy_s3(self, region, account_id)
    )
    new_role.add_to_policy(
        # CloudWatch log
        policy.create_policy_lambda_log(self, region, account_id)
    )
    # Rekognition roles
    new_role.add_to_policy(
        policy.create_policy_rekognition(self, region, account_id)
    )
    new_role.add_to_policy(
        policy.create_policy_passrole_rekognition(self, region, account_id)
    )
    new_role.add_to_policy(
        policy.create_policy_sns(self, region, account_id)
    )
    # Invoke step function, lambda
    new_role.add_to_policy(
        _iam.PolicyStatement(
            actions=["states:*", "lambda:GetFunctionConfiguration"],
            resources=["*"]
        )
    )
    return new_role