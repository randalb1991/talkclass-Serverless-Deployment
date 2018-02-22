# VIA API
# Pending to implement queryparameters
__author__ = 'Randal'
import boto3, os
import datetime
import hashlib
import json
def return_error(statusCode, message):
    response = {
        "statusCode": statusCode,
        "headers": {
            "Access-Control-Allow-Origin" : "*"
            },
        "body": message
    }
    return response

def handler(event, context):
    tags = []
    #Values checker
    print("Event Initial: "+str(event))
    if 'body' in event:
        # Si el evento se llama desde apigateway(Lambda Proxy), el evento original vendra en el body
        # Y nos los quedaremos. Si no, usamos el evento original ya que traera todos los datos
        event = json.loads(event['body'])
    print("Event took(Body): "+str(event))

    if 'username' not in event:
        return return_error(400, "Username not given")
    username = event["username"]
    user = get_user_given_username(username)
    if username is False:
        return return_error(404, "User doesn't exist in Dynamo DB ")
    user_dic = parse_dynamo_response(user)
    if user_dic is False:
        return return_error(500, "Error parsing the user obtained from Dynamo DB")
    return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin" : "*"
                },
            "body": json.dumps(user_dic)
            }
# Notification
def parse_dynamo_response(user):
    user_dict = {}
    print("Parsing the user given from dynamo")
    try:
        for key, value in user.items():
            for k, v in value.items():
                user_dict[key] = v
        print("New User dic "+str(user_dict))
        return user_dict
    except Exception as e:
        print("Error parsing user obtaied from dynamo db to User Dic")
        return False
        #print json.dumps(dict(item))

def get_user_given_username(username):
    print("Getting user")
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableUsers'],#"Users",#
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Username':{
                'AttributeValueList': [{
                    'S': username
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
            }
    )
    try:
        return response["Items"][0]
    except IndexError as ie:
        print("Error in index "+str(ie))
        return False
    except KeyError as ke:
        print("Error in key "+str(ke))
        return False
