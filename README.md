
# Amazon Rekognition Video Moderation - image sampling solution

Amazon Rekognition is an AWS AI service that offers pre-trained APIs to support image and video moderation. 

<!--
One approach to moderate videos is to model video data as a sample of image frames and use image content moderation models to process the frames individually. 
For more information about Rekognition video moderation comparision, refer to [this blog post](https://aws.amazon.com/blogs/machine-learning/how-to-decide-between-amazon-rekognition-image-and-video-api-for-video-moderation/) which compares the image and video APIs in terms of accuracy, cost, performance and architectural complexity.
-->
This repo contains two solutions to help you to implement video moderation using Rekognition image API. 
Both solutions offer a similar interface as the Rekognition Video moderation API, which can invoke asynchronizely and send moderation results to an SNS topic.
So you can easily replace your logic to switch to Image moderation API.

You can deploy the two solutions to your AWS account using CDK by following the instruction.

### Solution I: All-in-one Lambda function
The Lambda function manages the below logical steps in one place:
1. Download the video from the S3 bucket to the local disk
2. Sample images from the video based on a given interval using ffmpeg (default interval: 2 frames per second)
3. Store the images in S3 bucket in a temperate folder
4. Call Rekognition Image API to moderate the image frames
5. Consolidate the result to the Rekognition Video moderation API response format
6. Send the result to an SNS topic (if provided)

[Lambda source code](lambda/all-in-one/rek-video-image-sampling.py)

[Deployment logic with Lambda Layer](video_sampling/lambda_stack.py)

Invoke the Lambda function from your existing code in async mode as below:
```
import boto3, json
lambda_client = boto3.client("lambda")

lambda_client.invoke_async(
    FunctionName='TheLambdaFunctionName',
    InvokeArgs=json.dumps(
        {
          "s3_source_bucket": "MyS3Bucket",
          "s3_source_key": "path/to/video.mp4",
          "s3_target_bucket": "OPTIONAL_BUCKET_KEEP_TEMP_FILES", # Optional. if you don't have read access to source bucket
          "s3_target_folder": "temp/folder", # Optional. Temp folder keeps staging files, such as sampled images and moderation result
          "sample_frequency": 2, # Optional. numbers of images per second
          "min_confidence": 50, # Optional. Confidence threshold
          "sns_topic_arn": "arn:aws:sns:us-east-1:122702569249:cm-rek-video-sampling-topic" # Optional
        }
    )
)

```
This solution is light to deploy but only suitable for short-form videos. It may timeout if the video is too long, with a high resolution, and requires to sample the video in a high frequency.
The max timeout setting for Lambda is 15 minutes.

### Solution II: Step Functions + Lambda
This solution uses Step Functions state machine to orchestrate Lambda functions. 
It prevents the timeout issue could happen in the first single Lambda function solution, as the workflow will iterate through the sampled images and call a Lambda function one by one.
It is ideal for use cases when you need to moderate large videos in a high frequency.

![Step Functions workflow digram](static/rek-video-sampling-stepfunctions.png)

Invoke Step Functions state machine using Boto3
```
import boto3, json
sfn_client = boto3.client('stepfunctions')

sfn_client.start_execution(
    stateMachineArn='StepFunctionStateMachineArn',
    name='GiveItAName',
    input=json.dumps(
        {
          "s3_source_bucket": "MyS3Bucket",
          "s3_source_key": "path/to/video.mp4",
          "s3_target_bucket": "OPTIONAL_BUCKET_KEEP_TEMP_FILES", # Optional. if you don't have read access to source bucket
          "s3_target_folder": "temp/folder", # Optional. Temp folder keeps staging files, such as sampled images and moderation result
          "sample_frequency": 2, # Optional. numbers of images per second
          "min_confidence": 50, # Optional. Confidence threshold
          "sns_topic_arn": "arn:aws:sns:us-east-1:122702569249:cm-rek-video-sampling-topic" # Optional
        }
    ),
)
```

[Step Functions source code](stepfunctions/rek-video-moderation-image-sampling.json)

[Lambda: capture images from video](lambda/capture-frames/rek-video-image-sampling-capture-frames.py)

[Lambda: moderate image](lambda/moderate-image/rek-video-image-sampling-moderate-image.py)

[Lambda: consolidation](lambda/consolidation/rek-video-image-sampling-consolidate.py)

[Deployment logic](video_sampling/stepfunction_stack.py)

You can test the Lambda or the Step Functions solutions directly by sending the JSON payload to the Lambda and Step Functions state machine using the AWS console, CLI, or SDK.

### Install environment dependencies and set up authentication
<details><summary>
:bulb: You can skip this section if using CloudShell to deploy the CDK package or the other AWS services support bash command from the same AWS account (ex. Cloud9). This section is required if you run from a self-managed environment such as a local desktop.
</summary>


- [ ] Install Node.js
https://nodejs.org/en/download/

- [ ] Install Python 3.7+
https://www.python.org/downloads/

- [ ] Install Git
https://github.com/git-guides/install-git

- [ ] Install Pip
```sh
python -m ensurepip --upgrade
```

- [ ] Install Python Virtual Environment
```sh
pip install virtualenv
```


- [ ] Setup the AWS CLI authentication
```sh
aws configure                                                                     
 ```                      
</details>

![Open CloudShell](static/cloudshell.png)

### Deploy the CDK package

1. Clone code
```sh
git clone https://github.com/lanazhang/aws-rekognition-video-moderation-image-sampling
```
```sh
cd aws-rekognition-video-moderation-image-sampling/
```

2. Install Node CDK package
```sh
sudo npm install -g aws-cdk
```

3. Create Python Virtual Environment
```sh
python3 -m venv .venv
```

4. Activate virtual environment

  - On MacOS or Linux
  ```sh
  source .venv/bin/activate
  ```
  - On Windows
  ```sh
    .venv\Scripts\activate.bat                                        
```

5. Once the virtualenv is activated, you can install the required dependencies.

```
pip install -r requirements.txt
```

6. Set up environment varaibles - change the values to your target AWS account Id and region.
```
export CDK_DEFAULT_ACCOUNT=[YOUR_ACCOUNT_ID]
export CDK_DEFAULT_REGION=[YOUR_TARGET_REGION]
```

7. Bootstrap CDK - this step will launch a CloudFormation stack to provision the CDK package, which will take ~2 minutes.
```
cdk bootstrap aws://${CDK_DEFAULT_ACCOUNT}/${CDK_DEFAULT_REGION}
```

8. Deploy CDK package - this step will launch both or one of the solutions, which will take ~5 minutes.
```
# Deloy both solutions
cdk deploy --all --requires-approval never
```
```
# Deloy the Lambda solution
cdk deploy LambdaAllInOneStack
```
```
# Deloy the Step Functions solution
cdk deploy StepFunctionWorkflowStack 
```
Once the deployment completes, you can find the Lambda or the Step Functions names in the bash console. You can also find them in the CloudFormation console by checking the output in stack **LambdaAllInOneStack** and **StepFunctionWorkflowStack**.

Both the Lambda Function and the Step Functions State Machine names are in the pattern of **rek-video-image-sampling-XXXX**