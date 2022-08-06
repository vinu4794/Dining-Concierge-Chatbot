import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import requests
dynamodb = boto3.resource('dynamodb')

ELASTIC_SEARCH_URL = "<ES_URL>"
SQS_URL = "<SQS_URL>"
SNS_TOPIC_ARN = "<SNS_ARN>"

def cacheRestaurantRecommendations(messageToCache):

    table_suggestion = dynamodb.Table('prevSuggestions')
    userName = "<username>";

    response = table_suggestion.scan(FilterExpression=Attr('userID').eq(userName))
    cache_item = response['Items'][0] if len(response['Items']) > 0 else None
    if response is None or cache_item is None:
        
        table_suggestion.put_item(
        Item = {
            'userID': userName,
            'prevSuggestions': messageToCache
        })
    else:
        table_suggestion.update_item(
            Key={'userID': userName},
        UpdateExpression="set prevSuggestions= :messageToCache",
        ExpressionAttributeValues={
            ':messageToCache': messageToCache
        },
        ReturnValues="UPDATED_NEW")

def lambda_handler(event, context):

    try:
        sqs_client = boto3.client("sqs", region_name="us-east-1")
    except Exception as e:
        print(e)
    queue_url = SQS_URL;

    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    
    message_data = response['Messages'][0]
    message_atributes = message_data['MessageAttributes']

    cuisine = message_atributes['cuisine']
    cuisine = cuisine['StringValue'] 

    city = message_atributes['location']
    location = city['StringValue']

    people_num = message_atributes['numberpeople']
    number_of_people = people_num['StringValue'] 
 
    phone = message_atributes['PhoneNumber']
    phone_number = phone['StringValue']
 
    time_data = message_atributes['time']
    time = time_data['StringValue']
  
    date = message_atributes['date']
    date = date['StringValue'] 
    
    if not cuisine or not phone_number:
        print("No Cuisine or Phone found in message")
        return
    print("Cuisine: {}, Phone number: {}, Time: {}, Date: {}, Number of people: {}".format(cuisine, phone_number, time, date, number_of_people))
    
    esUrl = ELASTIC_SEARCH_URL + "_search?q={cuisine}".format(cuisine=cuisine)

    esResponse = requests.get(esUrl, auth=("<USERNAME>", "<PASSWORD>"))

    data = json.loads(esResponse.content.decode('utf-8'))
    print(data);

    try:
        esData = data["hits"]["hits"]
    except KeyError:
        print("Error extracting hits from ES response")

    restaurant_ids = []
    for restaurant in esData:
        restaurant_ids.append(restaurant["_source"]["ID"])
    
    messageToSend = 'Hello! Here are the {cuisine} restaurant suggestions in {location} for {numPeople} people, for {diningDate} at {diningTime}: '.format(
            cuisine=cuisine,
            location=location,
            numPeople=number_of_people,
            diningTime=time,
            diningDate=date,
        )

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('yelp-restaurants')
    idx = 1 

    restaurant_ids = restaurant_ids[1:3]
    
    for id in restaurant_ids:
        response = table.get_item(Key = {"ID": id})

        item = response['Item']

        name = item['Name']
        address = item['Address']
        if response is None:
            continue
        restaurantMsg = '' + str(idx) + '. '
        name = item["Name"]
        address = item["Address"]
        restaurantMsg += name +', located at ' + str(address)[1:-1] +'. '
        messageToSend += restaurantMsg
        idx += 1

    messageToSend += "Enjoy your meal!!!"
    print("messageToSend: {}".format(messageToSend))
    sns = boto3.client('sns', region_name='us-east-1')
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Message=json.dumps(str(messageToSend)))
    except KeyError:
        print("Error sending ")
        sns.publish(TopicArn=SNS_TOPIC_ARN, Message=json.dumps("No recommendations found."))

    cacheRestaurantRecommendations(messageToSend);

    return {
        'statusCode': 200,
        'body': json.dumps(messageToSend)
    }