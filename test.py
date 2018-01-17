import boto3
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
        scan['Place'] = {
                            'AttributeValueList':[{
                                'S': classroom_invited
                                }
                                ],
                            'ComparisonOperator': 'CONTAINS'
                        }
    print scan
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName='Eventos',
        Select='ALL_ATTRIBUTES',
        ScanFilter=scan
    )
    return response["Items"]

print get_events_from_dynamoDB()