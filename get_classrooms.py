#VIA API
import json
import os
import boto3


def parse_dynamo_response(classrooms):
    classrooms_dict = []
    print("Parsing the user given from dynamo")
    try:
        for classroom in classrooms:
            classroom_dic = {}
            for key, value in classroom.items():
                for k, v in value.items():
                    classroom_dic[key] = v
            classrooms_dict.append(classroom_dic)
            print("New Classroom dic "+str(classroom_dic))
        return classrooms_dict
    except Exception as e:
        print("Error parsing user obtained from dynamo db to User Dic"+str(e))
        return False

def get_classrooms_from_dynamoDB(level):
    if level is None:
        scan = {}
    else:
        scan = {
            'Level': {
                'AttributeValueList':[{
                    'S': level
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableClassroom'],
        Select='ALL_ATTRIBUTES',
        ScanFilter=scan
    )
    return response["Items"]


def handler(event, context):
    level = None
    print("Event Initial: "+str(event))
    if 'queryStringParameters' in event:
        query = event['queryStringParameters']
        # Se mira si hay alguna query dentro de la URL para poder filtrar.
    if query is not None:
        if 'level' in query:
            level = query['level']
    response = get_classrooms_from_dynamoDB(level)
    print(response)
    classrooms = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(classrooms)
            }

def handler_with_path_parameters(event, context):
    level = None
    print("Event Initial: "+str(event))
    if 'pathParameters' in event:
        pathParameters = event['pathParameters']
        # Se mira si hay alguna query dentro de la URL para poder filtrar.
    if pathParameters is not None:
        if 'level' in pathParameters:
            level = pathParameters['level']
            print('Level given in path parameters: '+level)

    response = get_classrooms_from_dynamoDB(level)
    print(response)
    classrooms = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(classrooms)
            }