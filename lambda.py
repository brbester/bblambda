import os
import json
from botocore.vendored import requests
import urllib.parse
import boto3
import hashlib
import hmac
from boto3.dynamodb.conditions import Key, Attr


#Grab environment VARs
dynamoName = os.environ['DYNAMO_TABLE']
at =  os.environ['AT']
gapikey =  os.environ['G_API_KEY']
spark_key = str(os.environ['SPARK_KEY'])
botname =  os.environ['BOT_NAME']

#tie to DynamoDB Table
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(dynamoName)

#Functions for Cisco Spark API and Google API
def get_google(searchterm):
    URL = 'https://www.googleapis.com/customsearch/v1?key='+gapikey+'&q='+urllib.parse.quote(searchterm)
    print ("URL:"+URL+"\n")
    resp = requests.get(URL, verify=False)
    return json.loads(resp.text)

def get_me(at):
    headers = {'Authorization': _fix_at(at)}
    resp = requests.get(_url('/people/me'), headers=headers)
    # print (resp.text)
    me_dict = json.loads(resp.text)
    me_dict['statuscode'] = str(resp.status_code)
    return me_dict

def _url(path):
    return 'https://api.ciscospark.com/v1' + path


def _fix_at(at):
    at_prefix = 'Bearer '
    if at_prefix not in at:
        return 'Bearer ' + at
    else:
        return at

def get_message(at, messageId):
    headers = {'Authorization': _fix_at(at)}
    resp = requests.get(_url('/messages/{:s}'.format(messageId)), headers=headers)
    message_dict = json.loads(resp.text)
    message_dict['statuscode'] = str(resp.status_code)
    return message_dict

def post_message(at, roomId, text, markdown='', toPersonId='', toPersonEmail=''):
    headers = {'Authorization': _fix_at(at), 'content-type': 'application/json'}
    markdown = '> '+text
    payload = {'roomId': roomId, 'text': text, 'markdown':markdown}
    if toPersonId:
        payload['toPersonId'] = toPersonId
    if toPersonEmail:
        payload['toPersonEmail'] = toPersonEmail
    resp = requests.post(url=_url('/messages'), json=payload, headers=headers)
    message_dict = json.loads(resp.text)
    message_dict['statuscode'] = str(resp.status_code)
    return message_dict
    
def post_file(at, roomId, url, text='', toPersonId='', toPersonEmail=''):
    headers = {'Authorization': _fix_at(at), 'content-type': 'application/json'}
    payload = {'roomId': roomId, 'files': [url]}
    if text:
        payload['text'] = text
    if toPersonId:
        payload['toPersonId'] = toPersonId
    if toPersonEmail:
        payload['toPersonEmail'] = toPersonEmail
    resp = requests.post(url=_url('/messages'), json=payload, headers=headers)
    file_dict = json.loads(resp.text)
    file_dict['statuscode'] = str(resp.status_code)
    return file_dict    

#help list
def help(at, roomid):
    helpmessage=["**'help'** displays this message"]
    helpmessage.append("**'#history'** will list your last 10 requests to the bot")
    helpmessage.append("any other words will return Google search results")
    helpmd=""
    for line in helpmessage:
        helpmd = helpmd + "  \r\n > " + line
    resp2_dict = post_message(at,roomid, helpmd, helpmd)
    return resp2_dict

#history function
def history (at, roomid, email):
    response = table.query(
        IndexName='personEmail-created-index',
        KeyConditionExpression='personEmail = :email',
        ExpressionAttributeValues={":email":email},
        ScanIndexForward=False,
        Limit=10
    )
    items = response['Items']
    message=[]
    for item in items:
        message.append("**'"+item['text']+"'** at "+str(item['created']))
    md=""
    for line in message:
        md = md + "  \r\n > " + line
    resp2_dict = post_message(at,roomid, md, md)   
    
#Main Lambda Event Handler - received event{} from API Gateway POST
def lambda_handler(event, context):

    #Spark secret comparison to validate webhook
    hashed1 = event['headers']['X-Spark-Signature']
    hashed2 = hmac.new(spark_key.encode('utf8'), event['body'].encode('utf8'),hashlib.sha1).hexdigest()
    if hashed1 !=  hashed2:
        return ("Invalid Webhook")
 
    webhook = json.loads(event['body'])

    message = get_message(at, webhook['data']['id'])

    table.put_item(Item=message)

    if not (message['personId']==get_me(at)['id']): #loop prevention - won't respond to itself
        searchterm = message['text']
        roomid = message['roomId']
        if botname in searchterm:
            searchterm = searchterm[len(botname):]
        
        if 'help' in searchterm[0:5].lower() or '?' in searchterm[0:2]:
            help(at, roomid)
            quit()
        
        if '#history' in searchterm[0:9].lower():
            email = message['personEmail']
            history(at, roomid, email)
            quit()       
        
        
        resp_dict = get_google(searchterm)

        newmessage = "Response from Google: " + resp_dict["items"][0]["title"]+" "+resp_dict["items"][0]["link"]
        newmessage = newmessage.replace("<b>","")
        newmessage = newmessage.replace("</b>","")

        resp2_dict = post_message(at,roomid,newmessage)
        newmessage = "Response from Google: " + resp_dict["items"][1]["title"]+" "+resp_dict["items"][1]["link"]

        newmessage = newmessage.replace("<b>","")
        newmessage = newmessage.replace("</b>","")
        resp2_dict = post_message(at,roomid,newmessage)

        
        return 'Message Posted'
    return 'Bot Loop'
