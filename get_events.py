#VIA API
import json
import os
import boto3


def parse_dynamo_response(events):
    events_dict = []
    print("Parsing the user given from dynamo")
    try:
        for event in events:
            event_dic = {}
            for key, value in event.items():
                for k, v in value.items():
                    event_dic[key] = v
            events_dict.append(event_dic)
            print("New Classroom dic "+str(event_dic))
        return events_dict
    except Exception as e:
        print("Error parsing user obtained from dynamo db to User Dic"+str(e))
        return False

def get_events_from_dynamoDB(title=None, date=None, place=None, classroom_invited=None):
    scan = {}
    if title is not None:
        scan['Title'] = {
                            'AttributeValueList':[{
                                'S': title
                                }
                                ],
                            'ComparisonOperator': 'EQ'
                        }
    if date is not None:
        scan['Date'] = {
                            'AttributeValueList':[{
                                'S': date
                                }
                                ],
                            'ComparisonOperator': 'EQ'
                        }
    if place is not None:
        scan['Place'] = {
                            'AttributeValueList':[{
                                'S': place
                                }
                                ],
                            'ComparisonOperator': 'EQ'
                        }
    if classroom_invited is not None:
        scan['Classrooms'] = {
                            'AttributeValueList':[{
                                'S': classroom_invited
                                }
                                ],
                            'ComparisonOperator': 'CONTAINS'
                        }
    print('Scan')
    print(scan)
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName='Eventos',
        Select='ALL_ATTRIBUTES',
        ScanFilter=scan
    )
    return response["Items"]


def handler(event, context):
    title = None
    date = None
    place = None
    classroom_invited = None
    print("Executing handler")
    print("Event Initial: "+str(event))
    if 'queryStringParameters' in event:
        query = event['queryStringParameters']
        # Se mira si hay alguna query dentro de la URL para poder filtrar.
    if query is not None:
        if 'title'in query:
            title = query['title']
        if 'date' in query:
            date = query['date'].replace('-', '/')
        if 'place' in query:
            place = query['place']
        if 'classroom_invited' in query:
            classroom_invited = query['classroom_invited']
    response = get_events_from_dynamoDB(title=title, date=date,place=place,classroom_invited=classroom_invited)
    print(response)
    events = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(events)
            }

def handler_with_path_parameters(event, context):
    print("Executing handler_with_path_parameters")
    print("Event Initial: "+str(event))
    title = None
    date = None
    place = None
    classroom_invited = None
    if 'pathParameters' in event:
        pathParameters = event['pathParameters']
        # Se mira si hay alguna query dentro de la URL para poder filtrar.
    if pathParameters is not None:
        if 'date'in pathParameters:
            date = pathParameters['date'].replace('-', '/')
            print('Date given in path parameters: '+date)
        if 'title' in pathParameters:
            title = pathParameters['title']
            print('Title given in path parameters: '+title)
        if 'place' in pathParameters:
            # Doesn't used yet
            print('Place given in path parameters: '+place)
            place = pathParameters['place']
    response = get_events_from_dynamoDB(title=title, date=date,place=place,classroom_invited=classroom_invited)
    print(response)
    events = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(events)
            }
