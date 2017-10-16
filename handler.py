import requests
import json
import os

def handler(event, context):
    body = {
        "message": "Go Serverless v1.0! Your function executed successfully! "+os.environ["hello"],
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    """
    return {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "event": event
    }
    """
