import json
import boto3
import os
import subprocess

IMAGE_NAME_EXTENSION = '.png'
LOCAL_DIR = '/tmp'
SAMPLE_FREQUENCY = 2 # 2 image every 1 seconds
API_NAME = 'cm_video_moderation_image_sampling'

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')
sns = boto3.client('sns')

def lambda_handler(event, context):
    # -- Validate input parameters start -- 
    if event is None or "s3_source_bucket" not in event or "s3_source_key" not in event:
        return {
            'statusCode': 400,
            'body': 'Require parameters: s3_source_bucket and s3_source_key.'
        }
        
    s3_source_bucket = event["s3_source_bucket"]
    s3_source_key = event["s3_source_key"]
    sample_frequency = event.get("sample_frequency")
    if sample_frequency is None:
        sample_frequency = SAMPLE_FREQUENCY

    file_name = s3_source_key.split('/')[-1]
    local_file_path = f'{LOCAL_DIR}/{file_name}'

    s3_target_folder = event.get("s3_target_folder")
    if s3_target_folder is None:
        s3_target_folder = s3_source_key.replace(file_name, '')
    if s3_target_folder.endswith('/'):
        s3_target_folder = s3_target_folder[0:len(s3_target_folder)-1]

    s3_target_bucket = event.get("s3_target_bucket")
    if s3_target_bucket is None:
        s3_target_bucket = s3_source_bucket
    
    min_confidence = event.get("min_confidence")
    sns_topic_arn = event.get("sns_topic_arn")
    
    job_id = event.get("job_id")
    if job_id is None or len(job_id) == 0:
        job_id = f'{s3_source_bucket}_{s3_source_key}'.replace('/','_').replace('.','_')
    # -- Validation end --
    
    # Download video to local disk
    s3.download_file(s3_source_bucket, s3_source_key, local_file_path)
    
    # Sample images based on given interval and store images to local disk
    ffmpeg_cmd = f"/opt/bin/ffmpeg -i {local_file_path} -r {sample_frequency} {LOCAL_DIR}/%07d{IMAGE_NAME_EXTENSION}"
    cmd = ffmpeg_cmd.split(' ')
    p1 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Target folder: using the video file name as a sub folder
    s3_target_folder += "/" + file_name.lower()

    # Upload images to s3 and cleanup temp files on local disk
    labels = []
    for file in os.listdir(LOCAL_DIR):
        if file.endswith(IMAGE_NAME_EXTENSION):
            # convert file name from sequence to time position
            seq = float(file.replace(IMAGE_NAME_EXTENSION,''))
            ms_pos = 1/sample_frequency * (seq-1) * 1000
            s3.upload_file(f'{LOCAL_DIR}/{file}', s3_target_bucket, f'{s3_target_folder}/{ms_pos}.png')
            
            # moderate image
            mr = moderate_image(s3_target_bucket, f'{s3_target_folder}/{ms_pos}.png', min_confidence=min_confidence)
            if mr is not None and len(mr["ModerationLabel"]) > 0:
                labels.append(mr)
            
        # Delete local file: image or video
        os.remove(f'{LOCAL_DIR}/{file}')
    
    # sort labels
    labels.sort(key=lambda x: x["Timestamp"], reverse=False)
    
    result = {
            "JobId": job_id,
            "API": API_NAME,
            "Video": {
                "S3Bucket": s3_source_bucket,
                "S3ObjectName": s3_source_key
            },
            "ModerationLabels": labels
        }
        
    # send result to SNS topic
    if sns_topic_arn is not None:
        sns_response = sns.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps(result)
        )
        print(sns_response)

    return {
        'statusCode': 200,
        'body': result
    }

def moderate_image(s3_bucket, s3_key, min_confidence=50):
    ts = s3_key.split('/')[-1].replace(IMAGE_NAME_EXTENSION,'')
    detectModerationLabelsResponse = rekognition.detect_moderation_labels(
           Image={
               'S3Object': {
                   'Bucket': s3_bucket,
                   'Name': s3_key,
               }
           },
           MinConfidence=min_confidence,
    
        )
    result = {"Timestamp": float(ts), "ModerationLabel": []}
    for l in detectModerationLabelsResponse["ModerationLabels"]:
        result["ModerationLabel"].append(
            {
                "Confidence": l["Confidence"],
                "Name": l["Name"],
                "ParentName": l["ParentName"]
            }
        )
    return result