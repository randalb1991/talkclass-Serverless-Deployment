# Trigger
__author__ = 'Randal'
import boto3
import os


def handler(event, context):
    print("Event: "+str(event))
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            date = record["dynamodb"]['NewImage']['Date']['S']
            title = record["dynamodb"]['NewImage']['Title']['S']
            description = record["dynamodb"]['NewImage']['Description']['S']
            place = record["dynamodb"]['NewImage']['Place']['S']
            classrooms = record["dynamodb"]['NewImage']['Classrooms']['SS']
            send_notification_event(classrooms=classrooms, title=title, date=date, description=description, place=place)

        if record['eventName'] == 'MODIFY':
            date = record["dynamodb"]['NewImage']['Date']['S']
            title = record["dynamodb"]['NewImage']['Title']['S']

            new_description = record["dynamodb"]['NewImage']['Description']['S']
            old_description = record["dynamodb"]['OldImage']['Description']['S']

            new_place = record["dynamodb"]['NewImage']['Place']['S']
            old_place = record["dynamodb"]['OldImage']['Place']['S']

            new_classrooms = record["dynamodb"]['NewImage']['Classrooms']['SS']
            old_classrooms = record["dynamodb"]['OldImage']['Classrooms']['SS']

            if ((new_description != old_description) or (new_place != old_place)):
                # If description or place has been changed, the email is going to send to all classrooms
                send_notification_event(classrooms=new_classrooms, title=title, date=date, description=new_description,
                                        place=new_place, is_updated=True)
            else:
                old_classrooms = set(old_classrooms) #set old classrooms
                new_classrooms = set(new_classrooms) #set new classrooms
                difference_classrooms = (old_classrooms-new_classrooms)
                # Getting the new classroom added to send it the email
                print("Difference classrooms "+str(difference_classrooms))
                send_notification_event(classrooms=difference_classrooms, title=title, date=date,
                                        description=new_description, place=new_place, is_updated=True)

def send_notification_event(classrooms, title, description, date, place, is_updated=False):
    print("Sending Notification")
    sns = boto3.resource('sns')
    if is_updated:
        subject = "Event updated: "+title
    else:
        subject = "New event: "+title

    messagge = "A new event has been created and you, and your family are invited:\n\n" \
               "\t Title: " + title + "\n" \
               "\t Description: " + description + "\n" \
               "\t Date: " + date + "\n" \
               "\t Place : " + place + "\n\nHope to see you soon! \n\n Best Regards, \n\n Talkclass"
    print("Message generated: "+messagge)
    for classroom in classrooms:
        print("Classroom: "+classroom)
        arn = get_arn_of_classroom(classroom)
        print("The arn for the classroom "+classroom + " is "+arn)
        topic = sns.Topic(arn)
        response = topic.publish(
            Message=messagge,
            Subject=subject
        )
        print("Publish response:\n "+response)

def get_arn_of_classroom(classroom):
    print(classroom)
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
