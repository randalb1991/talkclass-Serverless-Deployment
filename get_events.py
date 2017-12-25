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

def get_events_from_dynamoDB(title):
    if title is None:
        scan = {}
    else:
        scan = {
            'Title': {
                'AttributeValueList':[{
                    'S': title
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableEvents'],
        Select='ALL_ATTRIBUTES',
        ScanFilter=scan
    )
    return response["Items"]


def handler(event, context):
    title = None
    print("Event Initial: "+str(event))
    if 'queryStringParameters' in event:
        query = event['queryStringParameters']
        # Se mira si hay alguna query dentro de la URL para poder filtrar.
    if query is not None:
        if 'title' in query:
            title = query['title']
    response = get_events_from_dynamoDB(title)
    print(response)
    events = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(events)
            }
