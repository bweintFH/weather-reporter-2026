import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables once
load_dotenv()

@st.cache_resource
def init_dynamodb():
    """ Initializes the DynamoDB connection globally """
    return boto3.resource(
        'dynamodb',
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN')
    )

@st.cache_data(ttl=86400) # Cache strictly for 24 hours
def get_cached_airports():
    """ 
    Fetches ALL airports from DynamoDB exactly ONCE.
    This cache is shared across all pages in the Streamlit app.
    """
    dynamodb = init_dynamodb()
    table = dynamodb.Table('Airports')
    
    airports = []
    response = table.scan()
    items = response.get('Items', [])
    
    # Handle pagination for large tables
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
        
    for item in items:
        icao = item.get('icao_code', '')
        if icao:
            airports.append({
                'icao_code': icao,
                'name': item.get('name', 'Unknown'),
                'label': f"{icao} - {item.get('name', 'Unknown')}",
                'lat': float(item.get('latitude', item.get('lat', 0.0))),
                'lon': float(item.get('longitude', item.get('lon', 0.0)))
            })
            
    return sorted(airports, key=lambda x: x['label'])

def fetch_weather_history(icao_code):
    """ Fetches historical weather data from DynamoDB (Not cached, as it updates every 30 mins) """
    dynamodb = init_dynamodb()
    table = dynamodb.Table('WeatherHistory')
    response = table.query(KeyConditionExpression=Key('icao_code').eq(icao_code))
    items = response.get('Items', [])
    
    formatted_data = []
    for item in items:
        timestamp_ms = int(item.get('timestamp', 0))
        readable_time = datetime.fromtimestamp(timestamp_ms / 1000.0)
        formatted_data.append({
            'Time': readable_time,
            'Temperature (°C)': float(item.get('temperature_c', 0)),
            'Humidity (%)': float(item.get('humidity_percent', 0)),
            'QNH (hPa)': float(item.get('qnh_hpa', 0)),
            'Wind': item.get('wind_readable', ''),
            'Raw METAR': item.get('raw_metar', '')
        })
    return formatted_data