#VIA API
import json
import os
import boto3


def parse_dynamo_response(multimedias):
    multimedias_dict = []
    print("Parsing the users given from dynamo")
    try:
        for multimedia in multimedias:
            multimedia_dic = {}
            for key, value in multimedia.items():
                for k, v in value.items():
                    multimedia_dic[key] = v
            multimedias_dict.append(multimedia_dic)
            print("New multimedia dic "+str(multimedia_dic))
        return multimedias_dict
    except Exception as e:
        print("Error parsing user obtained from dynamo db to multimedia Dic"+str(e))
        return False

def get_multimedias_from_dynamoDB(event_date=None, event_title=None, multimedia_title=None, format=None, tag=None, username=None):
    scan = {}
    if username is not None:
        scan['Username'] = {
                'AttributeValueList':[{
                    'S': username
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if event_title is not None:
        scan['Event'] = {
                'AttributeValueList':[{
                    'S': event_title
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if event_date is not None:
        scan['Date'] = {
                'AttributeValueList':[{
                    'S': event_date
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if multimedia_title is not None:
        scan['Title'] = {
                'AttributeValueList':[{
                    'S': multimedia_title
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }
    if format is not None:
        scan['Title'] = {
                'AttributeValueList':[{
                    'S': '.'+format
                    }
                    ],
                'ComparisonOperator': 'CONTAINS'
                }
    if tag is not None:
        scan['Tags'] = {
                'AttributeValueList':[{
                    'S': tag
                    }
                    ],
                'ComparisonOperator': 'CONTAINS'
                }

    print("--Scan--")
    print (scan)
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableMultimedia'],
        Select='ALL_ATTRIBUTES',
        ScanFilter=scan
    )
    return response["Items"]


def handler(event, context):
    event_title, event_date, tag, format, multimedia_title, username = None, None, None, None, None, None
    print("Event Initial: "+str(event))
    if 'queryStringParameters' in event:
        query = event['queryStringParameters']
        # Se mira si hay alguna query dentro de la URL para poder filtrar.
    if query is not None:
        if 'tag' in query:
            tag = query['tag']
        if 'event_title' in query:
            event_title = query['event_title']
        if 'event_date' in query:
            event_date = query['event_date']
        if 'format' in query:
            format = query['format']
        if 'multimedia_title' in query:
            multimedia_title = query['multimedia_title']
        if 'owner' in query:
            username = query['owner']
    response = get_multimedias_from_dynamoDB(event_date=event_date, event_title=event_title, multimedia_title=multimedia_title, format=format, tag=tag, username=username)
    multimedias = parse_dynamo_response(response)
    return {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(multimedias)
            }
