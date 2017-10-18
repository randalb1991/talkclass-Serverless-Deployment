__author__ = 'Randal'
import boto3
import os

def lambda_handler(event, context):
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            insert_event(record)
            
def insert_event(record):
    date = record["dynamodb"]['NewImage']['Date']['S']
    title = record["dynamodb"]['NewImage']['Title']['S']
    description = record["dynamodb"]['NewImage']['Description']['S']
    place = record["dynamodb"]['NewImage']['Place']['S']
    classrooms = record["dynamodb"]['NewImage']['Classrooms']['SS']
    send_notification(classrooms, title, date, description, place)


def send_notification(classrooms, title, date, description, place):
    sns = boto3.resource('sns')
    message = generate_message (title, date, description, place)
    subject = "New event: "+title
    for classroom in classrooms:
        arn = get_arn_of_classroom(classroom)
        topic = sns.Topic(arn)
        response = topic.publish(
            Message=message,
            Subject=subject
        )
        print(response)


def generate_message(title, date, description, place):
    messagge = "A new event has been created and you, and your family are invited:\n\n" \
               "\t Title: " + title + "\n" \
               "\t Description: " + description + "\n" \
               "\t Date: " + date + "\n" \
               "\t Place : " + place + "\n\nHope to see you soon! \n\n Best Regards, \n\n Talkclass"
    return messagge


def get_arn_of_classroom(classroom):
    classs = classroom.split(" ")[0]
    level = classroom.split(" ")[1]
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
    return response["Items"][0]["Topic"]["S"]
