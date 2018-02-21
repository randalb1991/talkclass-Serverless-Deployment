import boto3
import requests

# Get the service client.
s3 = boto3.client(
    's3'#,
    #aws_access_key_id="ASIAIHVCAEDZRRVFFKHA",
    #aws_secret_access_key="/QiJ42Tmvs45BztoyFT+T5EIj0OaDCL/Hixh/hCy",
    #aws_session_token="FQoDYXdzEOH//////////wEaDHeu0IP1lrbb4dFd5CKnAqVXOdGxxwVV93JKUmTaW19pmL9ywBN1Hbw3tFEoxi0shh903X52vV/qJuTy12xSnEKLjjUhnEUcqSkmMlMctAXkZy/9IDY5UffWNSUkvWDoldvalxc5R+g5EKFyJKu8DKWRdf2Ib/copVeKH0Yhl5xC2dmqKgyQQPky2jyGh1a6kOzVHKzLLpPm2E9JcSHTKB5sgErvRFCgKCScuWBYiGQyjo4b5B7VSOzEIBlB4pMTuexfgQHbyZUPDLphhsVxIO6bV3kcl14HdBR7nG9x6KTKJdsaBOsngnCvEXWEfanUU7w0vJlUWvkMDdhaRSv9Mrel411kjN7GEvvDn5su/LUkzurn8al4BSWdXXmBeKIZBGgunrWoCDkLItkqvzXtVxoQ7TgNBZcol6Wo1AU=",
)
# Generate the URL to get 'key-name' from 'bucket-name'
url = s3.generate_presigned_url(
    ClientMethod='get_object',
    Params={
        'Bucket': 'talkclass-tcbucket3332',
        'Key': 'Events/Halloween/24-2-2018/mola25.png'
    }
)

# Use the URL to perform the GET operation. You can use any method you like
# to send the GET, but we will use requests here to keep things simple.
print url
