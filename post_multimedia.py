# VIA API
# Title needs the extension (.png, .jpg....)
__author__ = 'Randal'
import boto3, os
import datetime
import hashlib
import json
import base64
def return_error(statusCode, message):
    response = {
        "statusCode": statusCode,
        "headers": {
            "Access-Control-Allow-Origin": "*"
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

    if 'file' not in event:
        return return_error(400, "File to upload not given")
    if 'title' not in event:
        return return_error(400,  "Title not given")

    if 'session_token' not in event:
        return return_error(400, "Session Token not given")

    if 'event' not in event:
        return return_error(400, "Event not given")

    if 'event_date' not in event:
        return return_error(400, "Event_date not given")
    # Values checker

    # Values exists?
    event['username'] = get_user_given_token(event['session_token'])
    if event['username'] is False:
        return return_error(401, "Invalid aws session token ")

    if not exist_event(title=event['event'], event_date=event['event_date']):
        #rollback(event['picture_key'])
        return return_error(404,  "Event don't exists")

    try:
        s3_path = upload_file_to_s3(event=event['event'], date=event['event_date'], title=event['title'], file_encoded=event['file'])
    except:
        return return_error(500, "Error inserting the file in S3")

    response = insert_file_event_DynamoDB(event, s3_path)

    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        rollback(event['picture_key'])
        return return_error(500, "Error inserting the file. File deleted from s3")
    else:
        classrooms = get_classrooms_of_the_event(event['event'], event['event_date'])
        send_notification(classrooms, event)
        return {
            "statusCode": 200,
            "headers": {
            "Access-Control-Allow-Origin": "*"
            },
            "body": "File uploaded and saved correctly in dynamoDB"
            }
        #return "File uploaded and saved correctly in dynamoDB"

    """
    Comrpobar que la imagen existe en s3
    Enviar notificaciones. Primero se consulta las clases invitadas al evento. Y luego para cada una de las clases se manda una notificaicon
    """
# Notification

def upload_file_to_s3(event, file_encoded, title, date):
    s3_client = boto3.client('s3')
    file_path = '/tmp/'+title
    fh = open(file_path, "wb")
    fh.write(file_encoded.decode('base64'))
    fh.close()
    print('Correctly created in ' +file_path)
    try:
        with open(file_path, "wb") as fh:
            fh.write(file_encoded.decode('base64'))
        print('Correctly saved ' +file_path)
    except Exception:
        print("Error decoding and creating the file")
        raise
    s3_path = "Events/"+event+"/"+date.replace('/', '-')+"/"+title
    try:
        s3_client.upload_file(file_path, os.environ['originalBucket'], s3_path)
    except Exception:
        print("Error uploading the picture "+file_path+" to "+s3_path+" in the bucket "+os.environ['originalBucket'] +"")
        raise

    return s3_path

def get_user_given_token(session_token):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableUsersLogged'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Session Token':{
                'AttributeValueList': [{
                    'S': hashlib.sha1(session_token).hexdigest()
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
            }
    )
    try:
        return response["Items"][0]['Username']['S']
    except IndexError:
        return False
    except KeyError:
        return False

def get_classrooms_of_the_event(event, event_date):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableEvents'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Title':{
                'AttributeValueList': [{
                    'S': event
                    }
                    ],
                'ComparisonOperator': 'EQ'
                },
            'Date':{
                'AttributeValueList': [{
                    'S': event_date
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
            }
    )
    try:
        return response["Items"][0]["Classrooms"]["SS"]
    except IndexError:
        return False
    except KeyError:
        return False

def send_notification(classrooms, event):
    sns = boto3.resource('sns')
    message = generate_message (event)
    subject = event['event']+" : "+event['title']
    for classroom in classrooms:
        print classroom
        arn = get_arn_of_classroom(classroom.split()[0], classroom.split()[1])
        topic = sns.Topic(arn)
        response = topic.publish(
            Message=message,
            Subject=subject
        )
        print(response)

def generate_message(event):
    messagge = "Se ha agregado un nuevo:\n\n" \
               "\t User: " + event['username'] + "\n" \
               "\t Title : " + event['title'] + "\n"\
               "\t Event: " + event['event'] + "\n" \
               "\t Date: " + event['event_date'] + "\n"
    return messagge

def get_arn_of_classroom(classs, level):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableClassroom'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Class':{
                'AttributeValueList': [{
                    'S': classs
                    }
                    ],
                'ComparisonOperator': 'EQ'
                },
            'Level':{
                'AttributeValueList': [{
                    'S': level
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
            }
    )
    try:
        return response["Items"][0]["Topic"]["S"]
    except IndexError:
        return False
    except KeyError:
        return False
# Notification

def insert_file_event_DynamoDB(event, s3_path):
    client = boto3.client('dynamodb')
    response = client.put_item(
        TableName=os.environ['tableMultimedia'],
        Item={
            'Username': {
                'S': event["username"]
            },
            'Title': {
                'S': event["title"]
            },
            'Event': {
                'S': event["event"]
            },
            'Date': {
                'S': event["event_date"]
            },
            'Picture Key': {
                'S': s3_path
            },
            'Tags': {
                'SS': getLabels(s3_path)
            }
        }
    )
    return response


def insert_file_DynamoDB(event):
    client = boto3.client('dynamodb')
    response = client.put_item(
        TableName=os.environ['tableMultimedia'],
        Item={
            'Username': {
                'S': event["username"]
            },
            'Title': {
                'S': event["title"]
            },
            'Picture Key': {
                'S': event["picture_key"]
            },
            'Date': {
                'S': getDate()
            },
            'Tags': {
                'SS': getLabels()
            }
        }
    )
    return response


def getDate():
    return str(datetime.datetime.now()).split()[0]


def rollback(picture_key):
    client = boto3.client('s3')
    response = client.delete_object(
    Bucket=os.environ['originalBucket'],
    Key=picture_key,
    )

    response2 = client.delete_object(
    Bucket=os.environ['resizedBucket'],
    Key=picture_key,
    )
    print response
    print response2
    return (200 < response['ResponseMetadata']['HTTPStatusCode'] < 205) & (200 < response2['ResponseMetadata']['HTTPStatusCode'] < 205)


def exist_user(username):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableUsers'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Username':{
                'AttributeValueList':[{
                    'S': username
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    )
    return response["Count"] > 0


def exist_event(title, event_date):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableEvents'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Title': {
                'AttributeValueList':[{
                    'S': title
                    }
                    ],
                'ComparisonOperator': 'EQ'
                },
            'Date': {
                'AttributeValueList':[{
                    'S': event_date
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    )

    return response["Count"] > 0


def getLabels(picture_key):
    labels = []
    client = boto3.client('rekognition')
    response = client.detect_labels(
    Image={
        'S3Object': {
            'Bucket': os.environ['originalBucket'],
            'Name': picture_key,
        }
    },
    MaxLabels=int(os.environ['maxLabel'])
    )
    for label in response['Labels']:
        labels.append(label['Name'])
    return labels
