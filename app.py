#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import CfnParameter as _cfnParameter
from aws_cdk import Stack,CfnOutput
import uuid
from video_sampling.lambda_stack import LambdaStack
from video_sampling.stepfunction_stack import StepFunctionsStack


instance_hash = str(uuid.uuid4())[0:5]
app = cdk.App()

lambda_stack = LambdaStack(app, "LambdaAllInOneStack", 
    description="Rekognition video moderation image sampling solution - deploy the all-in-one lambda function",
    instance_hash_code=instance_hash,
)

stepfunction_stack = StepFunctionsStack(app, "StepFunctionWorkflowStack", 
    description="Rekognition video moderation image sampling solution - deploy the Step Functions state machine and related resources",
    instance_hash_code=instance_hash,
)

app.synth()