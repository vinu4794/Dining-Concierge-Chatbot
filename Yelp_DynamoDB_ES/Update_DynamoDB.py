import boto3
import datetime
import csv
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('yelp-restaurants')

with open('Manhattan_Restaurants.csv', encoding='utf-8', newline='') as f:
    reader=csv.reader(f)
    restaurants=list(reader)
restaurants=restaurants[1:]

for restaurant in restaurants:
    tableEntry = {
        'id': restaurant[0],
        'name': restaurant[1],
        'address': restaurant[2],
        'coordinates': restaurant[3],
        'numofreview': int(restaurant[4]),
        'rating': Decimal(restaurants[1][5]),
        'zipcode': restaurant[6],
        'cuisine': restaurant[7]
    }

    table.put_item(
        Item={
            'insertedAtTimestamp': str(datetime.datetime.now()),
            'ID': tableEntry['id'],
            'Name': tableEntry['name'],
            'Address': tableEntry['address'],
            'Coordinates': tableEntry['coordinates'],
            'NumOfReviews': tableEntry['numofreview'],
            'Ratings': tableEntry['rating'],
            'Zipcode': tableEntry['zipcode'],
            'Cuisine': tableEntry['cuisine']
        }
    )