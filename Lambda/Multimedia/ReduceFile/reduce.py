from __future__ import print_function
import boto3
import os
import sys
import uuid
from PIL import Image
import PIL.Image
     
s3_client = boto3.client('s3')
     
def resize_image(image_path, resized_path):
    with Image.open(image_path) as image:
        image.thumbnail(tuple(x / 2 for x in image.size))
        image.save(resized_path)
     
def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        total_path_to_key = record['s3']['object']['key']
        if "/" in total_path_to_key:
            sp = total_path_to_key.split('/')
            file_name = sp[-1] #Last file of array
            download_path = '/tmp/{}{}'.format(uuid.uuid4(), file_name)
            upload_path = '/tmp/resized-{}'.format(file_name)
            s3_client.download_file(bucket, total_path_to_key, download_path)
            resize_image(download_path, upload_path)
            s3_client.upload_file(upload_path, '{}resized'.format(bucket), total_path_to_key)
        else:
            download_path = '/tmp/{}{}'.format(uuid.uuid4(), total_path_to_key)
            upload_path = '/tmp/resized-{}'.format(total_path_to_key)
            s3_client.download_file(bucket, total_path_to_key, download_path)
            resize_image(download_path, upload_path)
            s3_client.upload_file(upload_path, '{}resized'.format(bucket), total_path_to_key)

"""
bucket = "talkclasstfg-bucket"
#total_path_to_key = 'ko/IMG_0341.JPG'
total_path_to_key = 'IMG_0347.JPG'
if "/" in total_path_to_key:
    sp = total_path_to_key.split('/')
    file_name = sp[-1] #Last file of array
    download_path = '/home/ec2-user/{}{}'.format(uuid.uuid4(), file_name)
    upload_path = '/home/ec2-user/resized-{}'.format(file_name)
    s3_client.download_file(bucket, total_path_to_key, download_path)
    resize_image(download_path, upload_path)
    s3_client.upload_file(upload_path, '{}resized'.format(bucket), total_path_to_key)
else:
    download_path = '/home/ec2-user/{}{}'.format(uuid.uuid4(), total_path_to_key)
    upload_path = '/home/ec2-user/resized-{}'.format(total_path_to_key)
    s3_client.download_file(bucket, total_path_to_key, download_path)
    resize_image(download_path, upload_path)
    s3_client.upload_file(upload_path, '{}resized'.format(bucket), total_path_to_key)
"""
