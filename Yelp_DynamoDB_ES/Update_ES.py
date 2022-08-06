from variables import * 
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch

import boto3
import requests
import json

host = '<ES_URL>' 
path = 'restaurants/Restaurant/' 
region = 'us-east-1' 
service = 'es'

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
yelp_restaurants_table = dynamodb.Table('yelp-restaurants')

index = 1

lastEvaluatedKey = None
table_items = []

while True:

    if lastEvaluatedKey == None:
        response = yelp_restaurants_table.scan()
    else:
        response = yelp_restaurants_table.scan(
        ExclusiveStartKey=lastEvaluatedKey
    )

    table_items.extend(response['Items'])

    if 'LastEvaluatedKey' in response:
        lastEvaluatedKey = response['LastEvaluatedKey']
    else:
        break

print(len(table_items))


for item in table_items:

    id = item['ID']
    cuisine = item['Cuisine']

    url = host + path
    payload = {'ID': id, "Cuisine": cuisine}
    response = requests.post(url, auth=("USERNAME", "PASSWORD"), json=payload)

    print("\n{}: {} - {}".format(index, cuisine, response.text))
    index = index + 1
