__author__ = 'Randal'
#VIA API
# It's the as same that login.py, but this also return the username within credential json
import requests
import json
import datetime
import os
import hashlib
import boto3


def return_error(statusCode, message):
    response = {
        "statusCode": statusCode,
        "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
        "body": message
    }
    return response

def get_token_auth0(user, password, clientid, db):
    headers = {
        "Content-Type": "application/json"
    }

    url_session = os.environ['urlSessionOauth']

    body = "{" +\
           "\"client_id\":" + " \"" + clientid + "\"," +\
           "\"username\":" + " \"" + user + "\","+"\"password\":" + \
           " \"" + password + "\","+"\"id_token\": \" \"," +\
           "\"connection\":" + " \"" + db + "\"," +\
           "\"grant_type\": \"password\"," + "\"scope\": \"openid\"," +\
           "\"device\":      \" \"" + "}"
    #print body
    response = requests.post(url_session, data=body, headers=headers)
    return response


def delegation(id_token, clientid):
    headers = {
        "Content-Type": "application/json"
    }

    url_session = os.environ['urlSessionDelegation']

    body = "{" +\
            "\"client_id\":" + " \"" + clientid + "\"," +\
            "\"grant_type\":  \"urn:ietf:params:oauth:grant-type:jwt-bearer\"," +\
            "\"id_token\":" + " \"" + id_token + "\"," +\
            "\"target\":" + " \"" + clientid + "\"," +\
            "\"scope\":  \"openid\"," +\
            "\"api_type\":  \"aws\"" +\
        "}"

    response = requests.post(url_session, data=body, headers=headers)
    return response



def login(username, password, clientid, db):

    # Petition AUTH0
    response = get_token_auth0(user=username, password=password, clientid=clientid, db=db)
    if response.status_code is not 200:
        return return_error(response.status_code, response.text['error_description'])

    j = json.loads(response.text)

    # Delegation

    response2 = delegation(j["id_token"], clientid)
    #print(response2.text)

    if response2.status_code is not 200:
        return return_error(response2.status_code, response2.text['error_description'])
    j2 = json.loads(response2.text)
    auth0_token_id = j['id_token']
    #print 'Auth0 id_token: '+ auth0_token_id
    aws_secret_key = j2['Credentials']['SecretAccessKey']
    #print 'Secret key: '+ aws_secret_key
    aws_access_key = j2['Credentials']['AccessKeyId']
    #print 'Access key: '+ aws_access_key
    session_token_aws = j2['Credentials']['SessionToken']
    #print 'Session token: '+ session_token_aws
    expiration = j2['Credentials']['Expiration']
    #print 'Expirtaion: '+ expiration

     # If the login is ok. We save the type of authentication: email or username
    if '@' in username:
        is_email_account = True
    else:
        is_email_account = False
    user = get_profile_from_dynamo(username, is_email_account)

    if user is False:
        response = {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": "User profile not found on dynamoDB"
        }
        return response
    profile = parse_dynamo_response(user)
    saveUserLogged(username=profile['Username'], id_token_auth0=auth0_token_id, secret_key=aws_secret_key, access_key=aws_access_key,
                   session_token=session_token_aws, expiration=expiration)
    credentials = {'access_key': aws_access_key, 'secret_key': aws_secret_key, 'session_token':  session_token_aws}
    body_response = {"credentials": credentials, "profile": profile}
    response3 = {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": json.dumps(body_response)
    }
    return response3
def get_profile_from_dynamo(username, is_email_account):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableUsers'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Email' if is_email_account else 'Username':{
                'AttributeValueList':[{
                    'S': username
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    )
    try:
        return response["Items"][0]
    except IndexError:
        return False
    except KeyError:
        return False
def parse_dynamo_response(user):
    user_dict = {}
    print("Parsing the user given from dynamo")
    try:
        for key, value in user.items():
            for k, v in value.items():
                user_dict[key] = v
        print("New User dic "+str(user_dict))
        return user_dict
    except Exception as e:
        print("Error parsing user obtained from dynamo db to User Dic")
        return False

def saveUserLogged(username, id_token_auth0, secret_key, access_key,session_token, expiration):
    """
    This function will save a item in the table users_logged with the information about the login(username, token, date)
    @id_token: Id token belong to AUTH0
    """
    client = boto3.client('dynamodb')
    response = client.put_item(
        TableName=os.environ['tableUsersLogged'],
        Item={
            'Username': {
                'S': username
            },
            'Auth0 token': {
                'S': hashlib.sha1(id_token_auth0).hexdigest()
            },
            'Access Key': {
                'S': hashlib.sha1(access_key).hexdigest()
            },
            'Secret Key': {
                'S': hashlib.sha1(secret_key).hexdigest()
            },
            'Session Token': {
                'S': hashlib.sha1(session_token).hexdigest()
            },
            'Expiration': {
                'S': expiration
            },
            'Date': {
                'S': getDate()
            }
        }
    )
    return response

def getDate():
    return str(datetime.datetime.now()).split()[0]

def handler(event, context):
    #Username can be a email or username. The code will return the real username as part of credentials
    print("Event Initial: "+str(event))
    if 'body' in event:
        # Si el evento se llama desde apigateway(Lambda Proxy), el evento original vendra en el body
        # Y nos los quedaremos. Si no, usamos el evento original ya que traera todos los datos
        event = json.loads(event['body'])
    print("Event took(Body): "+str(event))

    if 'role' not in event:
        response4 = {
            "statusCode": 400,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": "Role not given. should be parent or teacher"
            }
        return response4

    if 'username' not in event:
        response4 = {
            "statusCode": 400,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": "Username not given"
            }
        return response4

    if 'password' not in event:
        response4 = {
            "statusCode": 400,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": "Password not given"
            }
        return response4


    if event["role"] == "teacher":
        clientid = os.environ['clientIdTeacher']
        db = os.environ['connectionTeacher']
        return login(username=event["username"], password=event["password"], clientid=clientid, db=db)
    if event["role"] == "parent":
        clientid = os.environ['clientIdParent']
        db = os.environ['connectionParent']
        #print("Role given: "+event["role"])
        #print("Client ID: "+clientid)
        #print("DB: "+db)
        return login(username=event["username"], password=event["password"], clientid=clientid, db=db)

    return {
            "statusCode": 400,
            "headers": {
                    "Access-Control-Allow-Origin" : "*"
                    },
            "body": "Role not valid! \n Roles allowed: teacher o parent"
            }

