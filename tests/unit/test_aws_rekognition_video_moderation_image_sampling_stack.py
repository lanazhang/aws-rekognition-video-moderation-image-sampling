import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_rekognition_video_moderation_image_sampling.aws_rekognition_video_moderation_image_sampling_stack import AwsRekognitionVideoModerationImageSamplingStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_rekognition_video_moderation_image_sampling/aws_rekognition_video_moderation_image_sampling_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsRekognitionVideoModerationImageSamplingStack(app, "aws-rekognition-video-moderation-image-sampling")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
