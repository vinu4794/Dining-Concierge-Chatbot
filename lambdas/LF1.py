import json
import datetime
import time
import dateutil.parser
import logging
import boto3
import re
import os
dynamodb = boto3.resource('dynamodb')
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def elicit_slot(sessionAttributes, intentName, slots, slot_to_elicit, message):
    print("Debug: Session attr: ",sessionAttributes)
    if not message['content']:
        return {
            'sessionAttributes': sessionAttributes,
            'dialogAction': {
                'type': 'ElicitSlot',
                'intentName': intentName,
                'slots': slots,
                'slotToElicit': slot_to_elicit
            }
        }
    return {
        'sessionAttributes': sessionAttributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intentName,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def confirm_intent(sessionAttributes, intentName, slots, message):
    return {
        'sessionAttributes': sessionAttributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intentName,
            'slots': slots,
            'message': message
        }
    }

def close(sessionAttributes, fulfillment_state, message):
    response = {
        'sessionAttributes': sessionAttributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(sessionAttributes, slots):
    return {
        'sessionAttributes': sessionAttributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def tryExceptionBlock(func):

    try:
        return func()
    except KeyError:
        return None

def buildValidationOutput(isValid, violatedSlot, messageContent):
    if messageContent is None:
        return {
            "isValid": isValid,
            "violatedSlot": violatedSlot
        }

    return {
        'isValid': isValid,
        'violatedSlot': violatedSlot,
        'message': {'contentType': 'PlainText', 'content': messageContent}
    }

def isvalid_location(location):
    locations = ['manhattan']

    if not location:
        return buildValidationOutput(False, 'Location', '')
    
    if location.lower() not in locations:
        return buildValidationOutput(False, 'Location', 'Sorry, we only serve Manhattan now.')
    
    return buildValidationOutput(True,'','')

def isvalid_cuisine(cuisine):
    cuisines = ['indian', 'chinese', 'italian', 'japanese', 'mexican', 'american', 'arab', 'thai', 'korean'];
    
    if not cuisine:
        return buildValidationOutput(False, 'Cuisine', '')
    
    if cuisine.lower() not in cuisines:
        return buildValidationOutput(False, 'Cuisine', 'This cuisine is not available. Please try any of the following : Indian, Chinese, Italian, Japanese, Mexican, Arab, Thai, Korean')
    return buildValidationOutput(True,'','')
    
def isvalid_time(date,time):
    print("Debug: time is:",time)
    if not time:
        return buildValidationOutput(False,'BookingTime','')
    if datetime.datetime.strptime(date, '%Y-%m-%d').date() == datetime.date.today():
        if datetime.datetime.strptime(time, '%H:%M').time() <= datetime.datetime.now().time():
            return buildValidationOutput(False,'BookingTime','Please enter a Dining Time which is after the current time')
    return buildValidationOutput(True,'','')

def isvalid_date(date):
    print("Debug: Date is:",date)
    if not date:
        return buildValidationOutput(False,'BookingDate','')
    if datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
        return buildValidationOutput(False,'BookingDate','Please enter a Dining Date that is after the current date')
    return buildValidationOutput(True,'','')
    
def isvalid_phoneNumber(phoneNumber):
	if phoneNumber is not None:
		if not phoneNumber.isnumeric() or len(phoneNumber) != 10:
			return buildValidationOutput(False,'phone','Please enter a valid phone number.'.format(phoneNumber))
	return buildValidationOutput(True,'','')

def isvalid_people(num_people):
    if not num_people:
         return buildValidationOutput(False,'NoOfPeople','')
    num_people = int(num_people)
    if num_people > 20:
        return buildValidationOutput(False,'NoOfPeople','Sorry, the limit per reservation is upto 20 people.')
    return buildValidationOutput(True,'','')
    
    
def getLexPrevSuggestions():
    userName = 'cloudproj';
    dynamoTable = dynamodb.Table('prevSuggestions')
    response = dynamoTable.scan(FilterExpression=Attr('userID').eq(userName))
	
    item = response['Items'][0] if len(response['Items']) > 0 else None
    if response is None or item is None:
        return None
    else:
        return(item['prevSuggestions']);
        

def validateSlots(restaurant):
    
    location = restaurant['Location']
    cuisine = restaurant['Cuisine']
    bookingDate = restaurant['BookingDate']
    bookingTime = restaurant['BookingTime']
    noOfPeople = restaurant['NoOfPeople']
    phoneNumber = restaurant['PhoneNumber']
    userConfirmation = restaurant['userConfirmation']
    
    if userConfirmation is None:
        if not getLexPrevSuggestions() == None:
                suggestions = getLexPrevSuggestions()
                return buildValidationOutput(False,
                                        'userConfirmation',
                                        'I found the following restaurant suggestions from our previous communication - {} Do you want new suggestions (Yes/No) ?'.format(suggestions))
    
    if userConfirmation in [None, 'yes', 'Yes']:
    

        if not location or not isvalid_location(location)['isValid']:
            return isvalid_location(location)
        
        if not cuisine or not isvalid_cuisine(cuisine)['isValid']:
            return isvalid_cuisine(cuisine)
            
        if not bookingDate or not isvalid_date(bookingDate)['isValid']:
            return isvalid_date(bookingDate)
    
        if not bookingTime or not isvalid_time(bookingDate,bookingTime)['isValid']:
            return isvalid_time(bookingDate,bookingTime)
            
        if not noOfPeople or not isvalid_people(noOfPeople)['isValid']:
            return isvalid_people(noOfPeople)
            
        if not phoneNumber or not isvalid_phoneNumber(phoneNumber)['isValid']:
            return isvalid_phoneNumber(phoneNumber)
    
    return buildValidationOutput(True,'','')


def sendSQSData(dataToSend):
    
    sqs = boto3.client('sqs')
    queue_url = '<SQS_URL>'
    delaySeconds = 5

    messageAttributes = {
        'cuisine': {
            'DataType': 'String',
            'StringValue': dataToSend['Cuisine']
        },
        'location': {
            'DataType': 'String',
            'StringValue': dataToSend['Location']
        },
        "time": {
            'DataType': "String",
            'StringValue': dataToSend['BookingTime']
        },
        "date": {
            'DataType': "String",
            'StringValue': dataToSend['BookingDate']
        },
        'noOfPeople': {
            'DataType': 'Number',
            'StringValue': dataToSend['NoOfPeople']
        },
        "PhoneNumber": {
            'DataType': "String",
            'StringValue': dataToSend['PhoneNumber']
        }

    }
    messageBody=('Recommendation for the food')
    
    response = sqs.send_message(
        QueueUrl = queue_url,
        DelaySeconds = delaySeconds,
        MessageAttributes = messageAttributes,
        MessageBody = messageBody
        )
    return response['MessageId']

def createDiningSuggestions(event):
    location = tryExceptionBlock(lambda: event['currentIntent']['slots']['Location'])
    cuisine = tryExceptionBlock(lambda: event['currentIntent']['slots']['Cuisine'])
    bookingDate = tryExceptionBlock(lambda: event['currentIntent']['slots']['BookingDate'])
    bookingTime = tryExceptionBlock(lambda: event['currentIntent']['slots']['BookingTime'])
    noOfPeople = tryExceptionBlock(lambda: event['currentIntent']['slots']['NoOfPeople'])
    phoneNumber = tryExceptionBlock(lambda: event['currentIntent']['slots']['PhoneNumber'])
    userConfirmation = tryExceptionBlock(lambda: event['currentIntent']['slots']['userConfirmation'])

    
    if userConfirmation in ['no', 'No', 'NO']:
        return close(event['sessionAttributes'],
                    'Fulfilled',
                    {'contentType': 'PlainText',
                    'content': 'Thank you. Have a nice day :-)'})
                    
    sessionAttributes = event['sessionAttributes'] if event['sessionAttributes'] is not None else {}

    reservationData = json.dumps({
        'Location': location,
        'Cuisine': cuisine,
        'BookingDate': bookingDate,
        'BookingTime': bookingTime,
        'NoOfPeople': noOfPeople,
        "PhoneNumber":phoneNumber,
        "userConfirmation":userConfirmation
    })
    
    reservation = json.loads(reservationData)
    
    if event['invocationSource'] == 'DialogCodeHook':
        validationOutput = validateSlots(reservation)
        
        if not validationOutput['isValid']:
            slots = event['currentIntent']['slots']
            slots[validationOutput['violatedSlot']] = None
            
            return elicit_slot(
                sessionAttributes, event['currentIntent']['name'],
                slots, validationOutput['violatedSlot'],
                validationOutput['message']
            )

        finalSessionAttributes = event['sessionAttributes'] if event['sessionAttributes'] is not None else {}

        return delegate(finalSessionAttributes, event['currentIntent']['slots'])
      
    dataToSend = {
                    'Location': location,
                    'Cuisine': cuisine,
                    'BookingDate': bookingDate,
                    'BookingTime': bookingTime,
                    'NoOfPeople': noOfPeople,
                    "PhoneNumber":phoneNumber
                };
                
    sendSQSData(dataToSend);
    
    return close(event['sessionAttributes'],
             'Fulfilled', {'contentType': 'PlainText', 
			 'content': 'Restaurant suggestions have been sent to your email!'})

def greetingIntent(event):
    
    return {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType": "SSML",
              "content": "Hi there, how can I help?"
            },
        }
    }
    
def thankYouIntent(event):
    
    return {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType": "SSML",
              "content": "You’re welcome."
            },
        }
    }

def dispatch(event):

    intentName = event['currentIntent']['name']

    if intentName == 'DiningSuggestionsIntent':
        return createDiningSuggestions(event)
    elif intentName == 'GreetingIntent':
        return greetingIntent(event)
    elif intentName == 'ThankYouIntent':
        return thankYouIntent(event)
		
    raise Exception('Following Intent is not supported: ' + intentName);

def lambda_handler(event, context):
    
    os.environ['TZ'] = 'America/New_York';
    time.tzset();
    
    return dispatch(event)
