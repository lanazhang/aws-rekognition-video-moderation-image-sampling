import json
import boto3
import os
import subprocess

IMAGE_NAME_EXTENSION = '.png'
DEFAULT_OUTPUT_FOLDER = 'screenshot'
LOCAL_DIR = '/tmp'
SAMPLE_FREQUENCY = 0.5 # 1 image every 2 seconds
    
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
        s3_source_path = s3_source_key.replace(file_name,'')
        while s3_source_path.endswith('/'):
            s3_source_path = s3_source_path[0:len(s3_source_path)-1]
        s3_target_folder = f"{s3_source_path}/{DEFAULT_OUTPUT_FOLDER}"


    s3_target_bucket = event.get("s3_target_bucket")
    if s3_target_bucket is None:
        s3_target_bucket = s3_source_bucket
    
    min_confidence = event.get("min_confidence")
    sns_topic_arn = event.get("sns_topic_arn")
    # -- Validation end --
    
    # Download video to local disk
    s3.download_file(s3_source_bucket, s3_source_key, local_file_path)
    
    # Sample images based on given interval and store images to local disk
    ffmpeg_cmd = f"/opt/bin/ffmpeg -i {local_file_path} -r {sample_frequency} {LOCAL_DIR}/%06d{IMAGE_NAME_EXTENSION}"
    cmd = ffmpeg_cmd.split(' ')
    p1 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Target folder: using the video file name as a sub folder
    s3_target_folder += "/" + file_name.lower()

    # Upload images to s3 and cleanup temp files on local disk
    for file in os.listdir(LOCAL_DIR):
        if file.endswith(IMAGE_NAME_EXTENSION):
            # convert file name from sequence to time position
            seq = float(file.replace(IMAGE_NAME_EXTENSION,''))
            ms_pos = 1/sample_frequency * (seq - 1) * 1000
            s3.upload_file(f'{LOCAL_DIR}/{file}', s3_target_bucket, f'{s3_target_folder}/{ms_pos}.png')
            
        # Delete local file: image or video
        os.remove(f'{LOCAL_DIR}/{file}')

    output = event
    output["s3_target_temp_folder"] = s3_target_folder
    if event.get("s3_target_folder") is None:
        output["s3_target_folder"] = '/'.join(s3_target_folder.split('/')[0:-1])
    if event.get("s3_target_bucket") is None:
        output["s3_target_bucket"] = s3_target_bucket
    return output