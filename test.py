__author__ = 'Randal'
import requests
def handler2():
    response = requests.Response()
    response.status_code = 503
    return response

a = handler2()
print a.text
print a.status_code