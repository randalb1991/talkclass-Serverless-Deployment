__author__ = 'Randal'
import boto3
import datetime
import os

def handler(event, context=None):

    if not 'title' in event:
        return "The title cannot be empty"

    if not 'description' in event:
        return "The description cannot be empty"

    if not 'place' in event:
        return "The title cannot be empty"

    if not 'date' in event:
        return "The date cannot be empty"

    if not 'classrooms' in event:
        return 'Classrooms cannot be empty'

    if len(event['classrooms']) == 0:
        return 'Please, insert at least 1 classroom'


    if not valid_date(event["date"]):
        return "Invalid day. The day should has the format dd/mm/yyyy and should be posterior to the current day"

    if exist_event(event["title"], event["date"]):
        return "An event with the same name and day exist"

    valid, value = valid_classrooms(event["classrooms"])
    if not valid:
        return value

    response, message = create_folders_in_s3(event["title"], value, event['date'])

    if response is not 200:
        return message

    response = insert_in_dynamo(event)
    if response is not 200:
        return "Error creating the event in dynamo DB, Rollback done and folders deleted from s3 "+ str(response)

    return "Folder created correctly in S3 and a notification send to the topic"

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

def insert_in_dynamo(event):
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