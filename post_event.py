#VIA API

__author__ = 'Randal'
import boto3
import datetime
import os
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

def handler(event, context=None):

    print("Event Initial: "+str(event))
    if 'body' in event:
        # Si el evento se llama desde apigateway(Lambda Proxy), el evento original vendra en el body
        # Y nos los quedaremos. Si no, usamos el evento original ya que traera todos los datos
        event = json.loads(event['body'])
    print("Event took(Body): "+str(event))

    if not 'title' in event:
        return return_error(400, "The title cannot be empty")

    if not 'description' in event:
        return return_error(400, "The description cannot be empty")

    if not 'place' in event:
        return return_error(400, "The title cannot be empty")

    if not 'date' in event:
        return return_error(400, "The date cannot be empty")

    if not 'classrooms' in event:
        return return_error(400, 'Classrooms cannot be empty')

    if not 'photo_event' in event:
        return return_error(400, 'Photo event cannot be empty and it should be encoded64')
    if not 'photo_name' in event:
        return return_error(400, 'Photo name and extension are necessary: FE: example_picture.png')

    if len(event['classrooms']) == 0:
        return return_error(400, 'Please, insert at least 1 classroom')


    if not valid_date(event["date"]):
        return return_error(400, "Invalid day. The day should has the format dd-mm-yyyy and should be posterior to the current day")

    if exist_event(event["title"], event["date"]):
        return return_error(409, "An event with the same name and day exist")

    valid, value = valid_classrooms(event["classrooms"])
    if not valid:
        return return_error(400, value)

    response, message = create_folders_in_s3(event["title"], value, event['date'])

    if response is not 200:
        return return_error(response, message)

    # Saving the Picture in s3
    try:
        # Name used to save the picture. Its recovered from os environment
        # File's Extension
        photo_event_name = os.environ['photo_event_name']+'.'+event['photo_name'].split('.')[1]
        s3_path = upload_file_to_s3(event=event['title'], date=event['date'], title=photo_event_name, file_encoded=event['photo_event'])
    except Exception as e:
        print(e)
        return return_error(500, "Error inserting the file in S3")

    # Inserting in DynamoDB
    response = insert_in_dynamo(event, s3_path)
    if response is not 200:
        return return_error(response, "Error creating the event in dynamo DB, Rollback done and folders deleted from s3 ")

    # All ok 200 -> 200
    response_to_return = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin" : "*"
            },
        "body": "Folder created correctly in S3 and a notification send to the topic"
    }
    return response_to_return

def upload_file_to_s3(event, file_encoded, title, date):
    print("Uploading main imagen file to s3")
    print('event name '+event)
    print('date event '+date)
    print('title picture'+title)
    print(file_encoded)
    print(title)
    print(date)
    print(event)
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
def exist_event(title, date):
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
                    'S': date
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    )

    return response["Count"] > 0

def insert_in_dynamo(event, picture_key):
    client = boto3.client('dynamodb')
    response = client.put_item(
        TableName=os.environ['tableEvents'],
        Item={
            'Title':{
                'S': event["title"]
            },
            'Date':{
                'S': event["date"]
            },
            'Classrooms':{
                'SS': event["classrooms"]
            },
            'Description':{
                'S': event["description"]
            },
            'Place':{
                'S': event["place"]
            },
            'Picture':{
                'S': picture_key
            },
            'Tags': {
                'SS': getLabels(picture_key)
            }
        }
    )
    return response['ResponseMetadata']['HTTPStatusCode']


def create_folders_in_s3(title, dic, date):
    client = boto3.client('s3')
    print dic
    for classroom in dic:
        #folder = dic[classroom]["folder"]
        path ="Events/"+title+"/"+date.replace('/', '-')+"/"#folder+title+"/"
        response = client.put_object(
            Bucket=os.environ['originalBucket'],
            Body='',
            Key=path
        )

        if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
            return response['ResponseMetadata']['HTTPStatusCode'], "The folder for event cannot be created in the original bucket for the classroom " + classroom
        response = client.put_object(
            Bucket=os.environ['resizedBucket'],
            Body='',
            Key=path
            )
        if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
            return response['ResponseMetadata']['HTTPStatusCode'], "The folder for event cannot be created in the resized bucket for the classroom " + classroom

    return response['ResponseMetadata']['HTTPStatusCode'], "Original and resized folder created correctly for all classrooms"


def valid_classrooms(clasrooms):
    dic = {}

    for classroom in clasrooms:
        try:
            classs = classroom.split(" ")[0]
            level = classroom.split(" ")[1]
        except IndexError:
                return False, "Invalid format of class. The classroom should be similar to \"1A Infantil\"  "
        if exist_classroom(classs, level):
            values = {}
            arn = get_arn_of_classroom(classs, level)
            if arn:
                values["arn"] = arn
            else:
                return False, "The classroom " + classroom + " don't have a Topic"
            folder = get_folder_of_classroom(classs, level)
            if folder:
                values["folder"] = folder
            else:
                return False, "The classroom " + classroom + " don't have a folder in s3"
            dic[classroom] = values
        else:
            return False, "The classroom " + classroom + " don't exits"
    return True, dic


def exist_classroom(classs, level):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableClassroom'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Class': {
                'AttributeValueList':[{
                    'S': classs
                    }
                    ],
                'ComparisonOperator': 'EQ'
                },
            'Level': {
                'AttributeValueList':[{
                    'S': level
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    )
    return response["Count"] > 0


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


def get_folder_of_classroom(classs, level):
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
            'Level': {
                'AttributeValueList': [{
                    'S': level
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
            }
    )
    try:
        return response["Items"][0]["Folder"]["S"]
    except IndexError:
        return False
    except KeyError:
        return False


def valid_date(date):

    correctDate = None
    try:
        date = date.replace('-', '/')
        date = date.split("/")
        year = date[2]
        month = date[1]
        day = date[0]
    except IndexError:
        return False
    try:
        Date = datetime.datetime(year=int(year), month=int(month), day=int(day))
        current_day = datetime.datetime.now()
        correctDate = Date > current_day
    except ValueError:
        correctDate = False
    return correctDate

def getLabels(picture_key):
    print("getting labels")
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
        print(str(label['Name']))
        labels.append(label['Name'])
    return labels








