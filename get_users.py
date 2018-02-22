#VIA API
import json
import os
import boto3


def parse_dynamo_response(users):
    users_dict = []
    print("Parsing the users given from dynamo")
    try:
        for user in users:
            user_dic = {}
            for key, value in user.items():
                for k, v in value.items():
                    user_dic[key] = v
            users_dict.append(user_dic)
            print("New user dic "+str(user_dic))
        return users_dict
    except Exception as e:
        print("Error parsing user obtained from dynamo db to User Dic"+str(e))
        return False

def get_users_from_dynamoDB(username=None, email=None, role=None, classroom=None, phone=None, address=None):
    scan = {}
    if username is not None:
        scan['Username'] = {
                'AttributeValueList':[{
                    'S': username
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if role is not None:
        scan['Role'] = {
                'AttributeValueList':[{
                    'S': role
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if email is not None:
        scan['Email'] = {
                'AttributeValueList':[{
                    'S': email
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if phone is not None:
        scan['Phone'] = {
                'AttributeValueList':[{
                    'S': phone
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if address is not None:
        scan['Address'] = {
                'AttributeValueList':[{
                    'S': address
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if classroom is not None:
        scan['Classroom'] = {
                'AttributeValueList':[{
                    'S': classroom
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    print("--Scan--")
    print (scan)
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableUsers'],
        Select='ALL_ATTRIBUTES',
        ScanFilter=scan
    )
    return response["Items"]


def handler(event, context):
    username, email, role, classroom, address, phone = None, None, None, None, None, None
    print("Event Initial: "+str(event))
    if 'queryStringParameters' in event:
        query = event['queryStringParameters']
        # Se mira si hay alguna query dentro de la URL para poder filtrar.
    if query is not None:
        if 'username' in query:
            username = query['username']
        if 'email' in query:
            email = query['email']
        if 'role' in query:
            role = query['role']
        if 'addresss' in query:
            address = query['addresss']
        if 'phone' in query:
            phone = query['phone']
        if 'classroom' in query:
            classroom = query['classroom']
    response = get_users_from_dynamoDB(username=username, email=email, role=role, classroom=classroom, address=address, phone=phone)
    print(response)
    users = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(users)
            }


def handler_with_path_parameters(event, context):
    username = None
    print("Event Initial: "+str(event))
    if 'pathParameters' in event:
        pathParameters = event['pathParameters']
        # Se mira si hay alguna query dentro de la URL para poder filtrar.
    if pathParameters is not None:
        if 'username' in pathParameters:
            username = pathParameters['username']
            print('Username given in path parameters: '+username)

    response = get_users_from_dynamoDB(username=username)
    print(response)
    classrooms = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(classrooms)
            }
