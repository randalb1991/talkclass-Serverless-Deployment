__author__ = 'Randal'
import boto3
import os
def handler(event, context):
    print("Evento: "+str(event))
    if 'class' in event:
        classs = event["class"]
    else:
        return return_error(400, "Class not inserted")

    if 'level' in event:
        level = event["level"]
    else:
        return return_error(400, "Level not inserted")

    is_valid_class, message = is_valid_classroom(event["class"], event["level"])

    if not is_valid_class:
        print ("Class not valid format")
        return return_error(400, message)

    if exist_classroom(classs, level):
        print("The class already exist")
        return return_error(409, "The class already exist")

    return create_classroom(classs, level)



def create_classroom(classs, level):
    response, path = create_folder_in_bucket(classs, level)
    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        print("Bucket creation: Failed")
        return return_error(response['ResponseMetadata']['HTTPStatusCode'], "Error creating the folder in s3 \n"+response['ResponseMetadata'])
    response = create_topic(classs, level)

    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        print("Topic creation: Failed")
        rollback(s3=True, path=path, sns=False)
        return return_error(response['ResponseMetadata']['HTTPStatusCode'], "Error creating the topic. Rollback executed\n"+response['ResponseMetadata'])

    arn_topic = response['TopicArn']

    response = insert_in_dynamodb(classs, level, path, arn_topic)

    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        print("DynamoDB creation: Failed")
        rollback(s3=True, path=path, sns=True, topic=arn_topic)
        return return_error(response['ResponseMetadata']['HTTPStatusCode'], "Error Inserting in Dynamo DB. Rollback executed \n"+response['ResponseMetadata'])

    return "Classroom created correctly with a foler in "+path+" and SNS Topic "+arn_topic

def rollback(s3, path, sns, topic=None):
    if s3:
        delete_folder_in_s3(path)
    if sns:
        delete_topic(topic)

def delete_folder_in_s3(path):
    client = boto3.client('s3')
    response1 = client.delete_object(
    Bucket=os.environ['originalBucket'],
    Key=path
    )
    response2 = client.delete_object(
    Bucket=os.environ['resizedBucket'],
    Key=path
    )
    return response1, response2

def delete_topic(arn):
    client = boto3.client('sns')
    response = client.delete_topic(
        TopicArn=arn
    )
    return response

def insert_in_dynamodb(classs, level, path_s3, arn_topic):
    client = boto3.client('dynamodb')
    response = client.put_item(
        TableName=os.environ['tableClassroom'],
        Item={
            'Class':{
                'S': classs
            },
            'Level':{
                'S': level
            },
            'Folder':{
                'S': path_s3
            },
            'Topic':{
                'S': arn_topic
            }
        }
    )
    return response


def is_valid_classroom(classs, level):
    if level not in ["ESO", "Infantil", "Primaria", "Bachillerato"]:
        return False, "The Level should be 'Infantil', 'Primaria', 'ESO' or 'Bechillerato'"
    try:
        classs = int(classs[0])
    except Exception:
        return False, "The class must have the format: 1A, 2B, 3C..."
    return True, "The format of class is valid"


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


def create_folder_in_bucket(classs, level):
        client = boto3.client('s3')
        path = 'Classrooms/'+level+'/'+classs+'/'
        response = client.put_object(
            Bucket=os.environ['originalBucket'],
            Body='',
            Key=path
            )
        if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
            return response

        response = client.put_object(
            Bucket=os.environ['resizedBucket'],
            Body='',
            Key=path
            )

        return response, path

def create_topic(classs, level):
    client = boto3.client('sns')
    topic_name = classs+level
    response = client.create_topic(
        Name=topic_name
    )
    return response

def return_error(statusCode, message):
    response = {
        "statusCode": statusCode,
        "body": message
    }
    return response