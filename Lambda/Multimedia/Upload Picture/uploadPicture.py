__author__ = 'Randal'
import boto3, os
import datetime
import hashlib
def handler(event, context):
    tags = []
    #Values checker

    if 'picture_key'not in event:
        return "Picture key not given"

    if 'title' not in event:
        return "Title not given"

    if 'session_token' not in event:
        return "Session Token not given"

    # Values checker

    # Values exists?
    event['username'] = get_user_given_token(event['session_token'])
    if  event['username'] is  False:
        return "Invalid aws session token "

    if 'event'in event:
        if 'event_date' in event:
            if not exist_event(title=event['event'], event_date=event['event_date']):
                #rollback(event['picture_key'])
                return "Event don't exists"
            else:
                response = insert_file_event_DynamoDB(event)
        else:
            return "Given event but, not given event date"
    else:
        response = insert_file_DynamoDB(event)

    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        rollback(event['picture_key'])
        return "Error inserting the file. File deleted from s3"
    else:
        if 'event' in event:
            classrooms = get_classrooms_of_the_event(event['event'], event['event_date'])
            send_notification(classrooms, event)
        return "File uploaded and saved correctly in dynamoDB"

    """
    Comrpobar que la imagen existe en s3
    Enviar notificaciones. Primero se consulta las clases invitadas al evento. Y luego para cada una de las clases se manda una notificaicon
    """
# Notification
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

def insert_file_event_DynamoDB(event):
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
            'Event Date': {
                'S': event["event_date"]
            },
            'Picture Key': {
                'S': event["picture_key"]
            },
            'Date': {
                'S': getDate()
            },
            'Tags': {
                'SS': getLabels(event["picture_key"])
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