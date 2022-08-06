from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import requests
import boto3
import json

host = '<ES_URL>'
region = 'us-east-1'

index = 'restaurants'
typeVar = 'Restaurant'
service = 'es'

docObj = {
	"Restaurant": {
		"properties": {
			"RestaurantID": {
				"type": "text"
			},
			"Cuisines": {
				"type": "text"
			}
		}
	}
}

r = requests.put(host+'/'+index, auth=('USERNAME', 'PASSWORD'))