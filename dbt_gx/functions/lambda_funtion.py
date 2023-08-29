import json
import boto3
import os

def lambda_handler(event, context):
    sns_client = boto3.client('sns')
    topic_arn = os.environ['SNS_TOPIC_ARN']

    success_rate = event['success_rate']

    if success_rate >= 90:  # or whatever threshold you choose
        message = f"Great Expectations run was successful with a success rate of {success_rate}%"
        subject = "Great Expectations Run Successful"
    else:
        message = f"Great Expectations run failed with a success rate of {success_rate}%"
        subject = "Great Expectations Run Failed"

    sns_client.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject=subject
    )

    return {
        'statusCode': 200,
        'body': json.dumps(message)
    }
