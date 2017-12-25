# VIA API
__author__ = 'Randal'
import boto3
import requests
import datetime
import os
import json
def return_error(statusCode, message):
    response = {
        "statusCode": statusCode,
        "headers": {
            "Access-Control-Allow-Origin" : "*"
            },
        "body": message
    }
    return response

def handler(event, context):

    print("Event Initial: "+str(event))
    if 'body' in event:
        # Si el evento se llama desde apigateway(Lambda Proxy), el evento original vendra en el body
        # Y nos los quedaremos. Si no, usamos el evento original ya que traera todos los datos
        event = json.loads(event['body'])
    print("Event took(Body): "+str(event))

    if 'email' in event:
        if not valid_email(event["email"]):
            return return_error(400, "Invalid email. The mail must be of type myaccount@example.com")
    else:
        return return_error(400, "Email field is empty")

    if 'birthday' in event:
        if not valid_date(event["birthday"]):
            return return_error(400, "Birthday is not valid date. The formart must be of type dd/mm/yyyy")
    else:
        return return_error(400, "Birthday field is empty")

    if 'role' in event:
        if not valid_role(event["role"]):
            return return_error(400, "Invalid role. Only 'teacher' and 'parent' roles are accepted")
    else:
        return return_error(400, "Role field is empty")

    if 'phone' in event:
        if not valid_phone(event["phone"]):
            return return_error(400, "Invalid phone. This field only accept numbers with a minimum size of 9 ")
    else:
        return return_error(400, "Phone field is empty")

    if not 'first_name' in event:
        return return_error(400, "First name field is empty")

    if not 'username' in event:
        return return_error(400, "Username field is empty")

    if not 'password' in event:
        return return_error(400, "Password field is empty")

    if 'last_name' in event:
        if len(event["last_name"]) < 2:
            return return_error(400, "Last name field is short")
    else:
        return return_error(400, 'Last name is empty')

    if not 'address' in event:
        return return_error(400, "Address field is empty")

    if 'postal_code' in event:
        if not valid_postal_code(event["postal_code"]):
            return return_error(400, "Invalid code postal or empty. Should be only number with a length between 5 and 7 digits ")
    else:
         return return_error(400, "Postal code field is empty")

    if exist_user(event["username"]):
        return return_error(400, "Username is already exists")

    if event["role"] == "parent":
        try:
            classs = event["classroom"].split(" ")[0]
            level = event["classroom"].split(" ")[1]
        except IndexError:
            return return_error(400, "Invalid format of class or empty. The classroom should be similar to \"1A Infantil\"  ")
        if not exists_classroom(classs=classs, level=level):
            return return_error(400, "The classroom doesn't exists on the data base")
        creation_ok_message = signup_parent(event=event)


    if event["role"] == "teacher":
        if 'tutor_class' in event:
            try:
                classs = event["tutor_class"].split(" ")[0]
                level = event["tutor_class"].split(" ")[1]
            except IndexError:
                return return_error(400, "Invalid format of class. The classroom should be similar to \"1A Infantil\"  ")

            if not exists_classroom(classs=classs, level=level):
                return return_error(400,  "The classroom doesn't exists on the data base ")

            if has_tutor(classs=classs, level=level):
                return return_error(400,  "This class already has a tutor")
        creation_ok_message = signup_teacher(event=event)

    response_to_return = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin" : "*"
            },
        "body": creation_ok_message
    }
    return response_to_return

def signup_parent(event):
    client_id = os.environ['clientIdParent']
    connection = os.environ['connectionParent']
    #Creatin the user on auth0
    response = signup_auth0(client_id=client_id, username=event["username"], email=event["email"],
                            password=event["password"], connection=connection)

    if response.status_code is not 200:
        return "Error creating the user in auth0 \n", response._content


    #Creating the folder on S3
    response, path = create_folder_in_bucket(role=event["role"], username=event["username"])
    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        return "Error creating the folder in s3. Please delete manually the user in auth0 \n", response['ResponseMetadata']
        """
            Implementation of rollback pending. Rollback should delete the user on auth0
        """


    #Inserting the user on DynamoDB
    response = insert_parent(event=event, path=path)
    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        rollback(s3=True, path=path, auth0=True, client_id=client_id, connection=connection, username=event["username"])
        return "Error creating the user in DynamoDB. Rollback executed and folder "+path+" deleted from s3. . Please delete manually the user in auth0 \n", response['ResponseMetadata']
        """
            Implementation of rollback pending. Rollback should delete the user on auth0
        """

    response = subscribe_to_topic(event["email"], event["classroom"])

    if not response:
        rollback(s3=True, path=path, auth0=True, client_id=client_id, connection=connection, username=event["username"], dynamo=True)
        return "The user cannot be suscribed to the topic of the classroom. Rollback done and folder in s3 deleted. User deleted in dynamo db. Please delete manually the user in auth0 \n"

    return "User created correctly on Auth0, dynamoDB, s3, and subscribed to the topic of the classroom \n"


def signup_teacher(event):
    client_id = os.environ['clientIdTeacher']
    connection = os.environ['connectionTeacher']

    # Creating the user on auth0
    response = signup_auth0(client_id=client_id, username=event["username"], email=event["email"],
                            password=event["password"], connection=connection)

    if response.status_code is not 200:
        return "Error creating the user in auth0 \n", response._content

    # Creating the folder on S3
    response, path = create_folder_in_bucket(role=event["role"], username=event["username"])
    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        return "Error creating the folder in s3. Please delete manually the user in auth0 \n", response['ResponseMetadata']

    # Inserting the user on DynamoDB
    response = insert_teacher(event=event, path=path)
    if response['ResponseMetadata']['HTTPStatusCode'] is not 200:
        rollback(s3=True, path=path, auth0=True, client_id=client_id, connection=connection, username=event["username"])
        return "Error creating the user in DynamoDB. Rollback executed and folder "+path+" deleted from s3. . Please delete manually the user in auth0 \n", response['ResponseMetadata']

    # Subscribe to the topic of the classroom
    if 'tutor_class' in event:
        response = subscribe_to_topic(event["email"], event["tutor_class"])
        if not response:
            rollback(s3=True, path=path, auth0=True, client_id=client_id, connection=connection, username=event["username"], dynamo=True)
            return "The user cannot be suscribed to the topic of the classroom. Rollback done and folder in s3 deleted. User deleted in dynamo db. Please delete manually the user in auth0 \n"

    return "User created correctly on Auth0, dynamoDB, s3, and subscribed to the topic of the classroom \n"



def delete_user_from_dynamo(username):
    client = boto3.client('dynamodb')
    response = client.delete_item(
    TableName=os.environ['tableUsers'],
    Key={
        'Username': {
            'S': username}
        }
    )
    return response

def subscribe_to_topic(email, classroom):
    sns = boto3.resource('sns')
    arn = get_arn_of_classroom(classroom)
    if arn == False:
        return False
    topic = sns.Topic(arn)
    subscription = topic.subscribe(
    Protocol='email',
    Endpoint=email
    #futures: the arn can exist in dynamo but no in sns, so the subscribe will fail. For next version this error should be contemplated
)
    return True

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
    try:
        return response["Items"][0]["Topic"]["S"]
    except IndexError:
        return False
    except KeyError:
        return False



def rollback(s3, path, auth0, client_id, connection, username, dynamo=False):
    if s3:
        delete_folder_in_s3(path)
    #Pending the rollback for auth0
    if dynamo:
        delete_user_from_dynamo(username)


def delete_folder_in_s3(path):
    client = boto3.client('s3')
    client.delete_object(
    Bucket=os.environ['originalBucket'],
    Key=path
    )
    client.delete_object(
    Bucket=os.environ['resizedBucket'],
    Key=path
    )




def signup_auth0(client_id, username, email, password, connection):
    headers = {
        "Content-Type": "application/json"
    }

    url_session = os.environ['urlSignUp']

    body = "{" +\
            "\"client_id\":" + " \"" + client_id + "\"," +\
            "\"username\":" + " \"" + username + "\"," +\
            "\"email\":" + " \"" + email + "\"," +\
            "\"password\":" + " \"" + password + "\"," +\
            "\"connection\":" + " \"" + connection +"\"" +\
        "}"
    print body
    response = requests.post(url_session, data=body, headers=headers)
    return response


def exist_user(username):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableUsers'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Username':{
                'AttributeValueList':[{
                    'S': username
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    )
    return response["Count"] > 0


def insert_teacher(event, path):
    if 'tutor_class'in event:
        tutorclass=event['tutor_class']
    else:
        tutorclass='-'
    client = boto3.client('dynamodb')
    response = client.put_item(
        TableName=os.environ['tableUsers'],
        Item={
            'Username':{
                'S': event["username"]
            },
            'Address':{
                'S': event["address"]
            },
            'Birthday':{
                'S': event["birthday"]
            },
            'Email':{
                'S': event["email"]
            },
            'First Name':{
                'S': event["first_name"]
            },
            'Last Name':{
                'S': event["last_name"]
            },
            'Phone':{
                'N': event["phone"]
            },
            'Role':{
                'S': event["role"]
            },
            'Tutor Class':{
                'S': tutorclass
            },
            'Postal Code':{
                'N': event["postal_code"]
            },
            'Folder':{
                'S': path
            }
        }
    )
    return response


def insert_parent(event, path):
    client = boto3.client('dynamodb')
    response = client.put_item(
        TableName=os.environ['tableUsers'],
        Item={
            'Username': {
                'S': event["username"]
            },
            'Address': {
                'S': event["address"]
            },
            'Birthday': {
                'S': event["birthday"]
            },
            'Email': {
                'S': event["email"]
            },
            'First Name': {
                'S': event["first_name"]
            },
            'Last Name': {
                'S': event["last_name"]
            },
            'Phone':{
                'N': event["phone"]
            },
            'Role': {
                'S': event["role"]
            },
            'Classroom': {
                'S': event["classroom"]
            },
            'Postal Code': {
                'N': event["postal_code"]
            },
            'Folder': {
                'S': path
            }
        }
    )
    return response


def valid_date(date):

    correctDate = None
    try:
        date = date.split("/")
        year = date[2]
        month = date[1]
        day = date[0]
    except IndexError:
        return False
    try:
        newDate = datetime.datetime(year=int(year), month=int(month), day=int(day))
        correctDate = True
    except ValueError:
        correctDate = False
    return correctDate


def valid_email(email):
    correct = None
    try:
        email = email.split("@")
        username = email[0]
        provider = email[1].split(".")[0]
        domain = email[1].split(".")[1]
        correct = (provider is not "") & (username is not "") & (domain is not "")
    except IndexError:
        correct = False

    return correct


def has_tutor(classs, level):
    client = boto3.client('dynamodb')
    response = client.scan(
        TableName=os.environ['tableUsers'],
        Select='ALL_ATTRIBUTES',
        ScanFilter={
            'Tutor Class':{
                'AttributeValueList':[{
                    'S': classs+ " "+ level
                    }
                    ],
                'ComparisonOperator': 'EQ'
                }

            }
    )
    return response["Count"] > 0


def valid_phone(phone):
    try:
        correct = len(phone) > 9
        phone = int(phone)
        return correct
    except ValueError:
        return False


def valid_role(role):
    return role == "parent" or role == "teacher"


def exists_classroom(classs, level):
    classs = classs
    level = level
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

    return response["Count"] > 0


def valid_postal_code(postal_code):
    if not postal_code:
        return False
    try:
        size = (len(postal_code) > 4) & (len(postal_code) < 8)
        postal_code = int(postal_code)
        return size
    except ValueError:
        return False


def create_folder_in_bucket(role, username):
        client = boto3.client('s3')
        path = None

        if role == "parent":
            path = 'Profiles/Parents/'+username+'/'
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
        if role == "teacher":
            path = 'Profiles/Teachers/'+username+'/'
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
