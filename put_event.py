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


def handler_with_path_parameters(event, context):
    print("Executing handler_with_path_parameters")
    print("Event Initial: "+str(event))

    # Checking pathParameters to take the date and title of the event
    if event['pathParameters'] is None:
        return return_error(404, "Path Parameters not given. URL used should be similar to /events/10-10-2018/halloween")
    else:
        pathParameters = event['pathParameters']


    if 'body' in event:
        # Si el evento se llama desde apigateway(Lambda Proxy), el evento original vendra en el body
        # Y nos los quedaremos. Si no, usamos el evento original ya que traera todos los datos
        event = json.loads(event['body'])

    if not 'date' in pathParameters:
        return return_error(404, "Date Path Parameters not given. URL used should be similar to /events/10-10-2018/halloween")
    else:
        if not pathParameters['date']:
            return return_error(404, "Date Path Parameters not given. URL used should be similar to /events/10-10-2018/halloween")
        date = pathParameters['date'].replace('-', '/')
        print('Date given in path parameters: '+date)

    if not 'title' in pathParameters:
        return return_error(404, "Title Path Parameters not given. URL used should be similar to /events/10-10-2018/halloween")
    else:
        if not pathParameters['title']:
            return return_error(404, "Title Path Parameters not given. URL used should be similar to /events/10-10-2018/halloween")
        title = pathParameters['title']
        print('Title given in path parameters: '+title)

    # Checking if exists event
    if not exist_event(title=title, date=date):
        return return_error(404, "Event "+title+" on "+date+" not found")

    # Check the new parameters

    if not 'description' in event:
        return return_error(400, "The description cannot be empty")
    else:
        new_description = event['description']
        print("new description "+new_description)

    if not 'place' in event:
        return return_error(400, "The place cannot be empty")
    else:
        new_place = event['place']
        print("new place "+new_place)

    if not 'classrooms' in event:
        return return_error(400, "Classroom to modify not given")
    else:
        # Checking classrooms
        classrooms = event["classrooms"]
        valid, value = valid_classrooms(classrooms)
        if not valid:
            return return_error(400, value)

    """
    #removed -> To modify date and title
    if not 'title' in event:
        return return_error(400, "The title cannot be empty")
    else:
        new_title = event['title']
        print("new title: "+new_title)
    # Checking date
    if not 'date' in event:
        return return_error(400, "The date cannot be empty")
    else:
        new_date = event['date']
        if not valid_date(new_date):
            return return_error(400, "Invalid day. The day should has the format dd-mm-yyyy and should be posterior to the current day")
        print("new date: "+new_date)

    # If the title or date are different, they need to be checked

    if (old_date == new_date) and (old_title == new_title):
        pass
    else:
        #Check if the event with the new data exists
        if exist_event(new_title, new_date):
            return return_error(409,  "Event "+new_title+" on "+new_date+" day exist")

    """


    response = update_item_in_dynamoDB(title=title, date=date, new_place=new_place,
                                       new_description=new_description, classrooms=classrooms)
    print(response)
    if response is not 200:
        return return_error(500, response)
#    events = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": 'juuuas'
            }

def update_item_in_dynamoDB(title, date, new_description, new_place, classrooms):
    client = boto3.client('dynamodb')
    response = client.update_item(
        TableName=os.environ['tableEvents'],
        Key={
            'Title': {
                'S': title
            },
            'Date': {
                'S': date
            }
        },
        AttributeUpdates={
        "Classrooms": {
            "Action": "ADD",
            "Value": {"SS": classrooms}
        },
        "Description": {
            "Action": "PUT",
            "Value": {"S": new_description}
        },
        "Place": {
            "Action": "PUT",
            "Value": {"S": new_place}
        }
    }
        )
    print response
    return response['ResponseMetadata']['HTTPStatusCode']


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
            return False, "The classroom " + classroom + " doesn't exits"
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

"""
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
"""


