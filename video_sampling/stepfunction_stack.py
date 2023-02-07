from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda,
    RemovalPolicy,
    aws_stepfunctions as _aws_stepfunctions,
)
from constructs import Construct
import os
from iam_role.lambda_all_in_one import create_role as create_lambda_all_in_one_role
from iam_role.lambda_capture_video_frame import create_role as create_lambda_capture_video_frame_role
from iam_role.lambda_moderate_image import create_role as create_lambda_moderate_image_role
from iam_role.lambda_consolidate import create_role as create_lambda_consolidate_role
from iam_role.lambda_step_functions import create_role as create_step_function_role

class StepFunctionsStack(Stack):
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
        # Lambda: rek-video-image-sampling-capture-frames
        lambda_capture_video_frames = _lambda.Function(self, 
            id='capture-frames', 
            function_name=f"rek-video-image-sampling-capture-frames-{self.instance_hash}", 
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='rek-video-image-sampling-capture-frames.lambda_handler',
            code=_lambda.Code.from_asset(os.path.join("./", "lambda/capture-frames")),
            timeout=Duration.seconds(900), # max timeout 15 minutes
            role=create_lambda_capture_video_frame_role(self, self.region, self.account_id),
            memory_size=10240,
            layers=[ffmpeg_layer]
        )

        # Lambda: rek-video-image-sampling-moderate-image
        lambda_moderate_image = _lambda.Function(self, 
            id='moderate-image', 
            function_name=f"rek-video-image-sampling-moderate-image-{self.instance_hash}", 
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='rek-video-image-sampling-moderate-image.lambda_handler',
            code=_lambda.Code.from_asset(os.path.join("./", "lambda/moderate-image")),
            timeout=Duration.seconds(10), # max timeout 15 minutes
            role=create_lambda_moderate_image_role(self, self.region, self.account_id),
            memory_size=1024,
        )

        # Lambda: rek-video-image-sampling-consolidate
        lambda_moderate_image = _lambda.Function(self, 
            id='consolidation', 
            function_name=f"rek-video-image-sampling-consolidate-{self.instance_hash}", 
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='rek-video-image-sampling-consolidate.lambda_handler',
            code=_lambda.Code.from_asset(os.path.join("./", "lambda/consolidation")),
            timeout=Duration.seconds(900), # max timeout 15 minutes
            role=create_lambda_consolidate_role(self, self.region, self.account_id),
            memory_size=10240,
        )        
        
        # StepFunctions StateMachine
        sm_json = None
        with open('./stepfunctions/rek-video-moderation-image-sampling.json', "r") as f:
            sm_json = str(f.read())

        if sm_json is not None:
            sm_json = sm_json.replace("##LAMBDA_CAPTURE_VIDEO_FRAMES##", f"arn:aws:lambda:{self.region}:{self.account_id}:function:rek-video-image-sampling-capture-frames-{self.instance_hash}")
            sm_json = sm_json.replace("##LAMBDA_MODERATE_IMAGE##", f"arn:aws:lambda:{self.region}:{self.account_id}:function:rek-video-image-sampling-moderate-image-{self.instance_hash}")
            sm_json = sm_json.replace("##LAMBDA_CONSOLIDATION##", f"arn:aws:lambda:{self.region}:{self.account_id}:function:rek-video-image-sampling-consolidate-{self.instance_hash}")
            
        cfn_state_machine = _aws_stepfunctions.CfnStateMachine(self, f'rek-video-sampling-workload-{self.instance_hash}',
            state_machine_name=f'rek-video-sampling-workload-{self.instance_hash}', 
            role_arn=create_step_function_role(self, self.region, self.account_id).role_arn,
            definition_string=sm_json)