from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda,
    RemovalPolicy
)
from constructs import Construct
import os
from iam_role.lambda_all_in_one import create_role as create_lambda_all_in_one_role

class LambdaStack(Stack):
    account_id = None
    region = None
    instance_hash = None

    def __init__(self, scope: Construct, construct_id: str, instance_hash_code: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.instance_hash = instance_hash_code

        self.account_id=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"])
        self.region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])

        # create Lambda layer
        ffmpeg_layer = _lambda.LayerVersion(self, 'ffmpeg_layer',
                                     code=_lambda.Code.from_asset(os.path.join("./", "lambda/layer")),
                                     description='Base layer with ffmpeg CLI',
                                     compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
                                     removal_policy=RemovalPolicy.DESTROY
                                     )
        # Create Lambdas
        # Lambda: rek-video-image-sampling
        lambda_s3_trigger = _lambda.Function(self, 
            id='s3-trigger', 
            function_name=f"rek-video-image-sampling-{self.instance_hash}", 
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='rek-video-image-sampling.lambda_handler',
            code=_lambda.Code.from_asset(os.path.join("./", "lambda/all-in-one")),
            timeout=Duration.seconds(900), # max timeout 15 minutes
            role=create_lambda_all_in_one_role(self, self.region, self.account_id),
            memory_size=10240,
            layers=[ffmpeg_layer]
        )
