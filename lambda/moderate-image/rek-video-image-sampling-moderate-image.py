import json
import boto3

IMAGE_NAME_EXTENSION = '.png'
DEFAULT_MIN_CONFIDENCE = 50

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

def lambda_handler(event, context):
    s3_bucket = event.get("s3_bucket")
    s3_key = event["s3_key"]["Key"]
    if not s3_key.endswith(IMAGE_NAME_EXTENSION):
        return "skip"
    
    min_confidence = event.get("min_confidence")
    if min_confidence is None:
        min_confidence = DEFAULT_MIN_CONFIDENCE
    
    if s3_bucket is None or s3_key is None:
        return {
            'statusCode': 400,
            'body': 'Required parameters: s3_bucket, s3_key'
        }

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
    
    if len(result["ModerationLabel"]) > 0:
        # Upload the result to S3
        s3.put_object(
            Body=json.dumps(result),
            Bucket=s3_bucket,
            Key=s3_key.replace(IMAGE_NAME_EXTENSION,'.json')
        )
        
    return result