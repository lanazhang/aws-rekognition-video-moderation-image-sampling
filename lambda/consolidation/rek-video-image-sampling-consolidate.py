import json
import boto3

API_NAME = 'cm_video_moderation_image_sampling'

s3 = boto3.client('s3')
sns = boto3.client('sns')

def lambda_handler(event, context):
    s3_source_bucket = event["Payload"].get("s3_source_bucket")
    s3_source_key = event["Payload"].get("s3_source_key")
    s3_target_folder = event["Payload"].get("s3_target_folder")
    s3_target_bucket = event["Payload"].get("s3_target_bucket")
    sns_topic_arn = event["Payload"].get("sns_topic_arn")
    job_id = event["Payload"].get("job_id")
    
    if job_id is None or len(job_id) == 0:
        job_id = f'{s3_source_bucket}_{s3_source_key}'.replace('/','_').replace('.','_')
        
    # get video file name from source key as sub folder
    file_name = s3_source_key.split('/')[-1]
    s3_target_folder += "/" + file_name.lower()

    # List JSON files in target S3 folder
    labels = []
    s3_response = s3.list_objects(Bucket=s3_target_bucket, Prefix=s3_target_folder)
    if s3_response is not None and "Contents" in s3_response:
        for c in s3_response["Contents"]:
            if c["Key"].endswith('.json'):
                s3_get_response = s3.get_object(Bucket=s3_target_bucket, Key=c["Key"])
                j = json.loads(s3_get_response["Body"].read().decode())
                if j is not None and "ModerationLabel" in j and len(j["ModerationLabel"]) > 0:
                    labels.append(j)
    
            # Delete file: image and json
            s3.delete_object(Bucket=s3_target_bucket, Key=c["Key"])
            
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
        
    # Send SNS message
    sns_response = sns.publish(
        TopicArn=sns_topic_arn,
        Message=json.dumps(result)
    )
    
    return {
        'statusCode': 200,
        'body': result
    }
