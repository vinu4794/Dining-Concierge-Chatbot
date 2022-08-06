import json
import boto3

def lambda_handler(event, context):
  client_lex = boto3.client('lex-runtime')
  response_lex = client_lex.post_text(
      botName='DiningBotThree',
      botAlias='diningbotalias',
      userId='cloudproj',
      inputText=event['messages'][0]['unstructured']['text']
    )
  response = {
    'statusCode':200,
    "messages": [
      {
        "type": "unstructured",
        "unstructured": {
          "text": response_lex['message'],
        }
      }
    ]
  }
  return response