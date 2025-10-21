import boto3
import os

print("Testing S3 access...")
print("S3_BUCKET_NAME:", os.getenv('S3_BUCKET_NAME'))
print("AWS_DEFAULT_REGION:", os.getenv('AWS_DEFAULT_REGION'))

try:
    s3 = boto3.client('s3')
    result = s3.list_objects_v2(Bucket='gladly-conversations-alai22', MaxKeys=1)
    print("Success! Found objects:", result.get('Contents', []))
except Exception as e:
    print("Error:", str(e))
