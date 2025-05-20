# weather.py
import requests
import xmltodict
from datetime import datetime
import os
from dotenv import load_dotenv


load_dotenv()
service_key = os.getenv("WEATHER_API_KEY")

# 기본 지역 정보 (필요시 추가 가능)
default_regions = [
    {"name": "서울", "nx": 60, "ny": 127},
    {"name": "부산", "nx": 98, "ny": 76},
    {"name": "대구", "nx": 89, "ny": 90},
    {"name": "광주", "nx": 58, "ny": 74},
    {"name": "인천", "nx": 55, "ny": 124},
    {"name": "강릉", "nx": 92, "ny": 131},
    {"name": "전주", "nx": 63, "ny": 89},
    {"name": "제주", "nx": 52, "ny": 38}
]

def get_current_date_string():
    return datetime.now().strftime("%Y%m%d")

def get_current_hour_string():
    now = datetime.now()
    hour = now.hour
    if now.minute < 45:
        hour = hour - 1 if hour > 0 else 23
    return f"{hour:02}30"

def fetch_weather_data(region):
    url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'
    params = {
        'serviceKey': service_key,
        'pageNo': '1',
        'numOfRows': '1000',
        'dataType': 'XML',
        'base_date': get_current_date_string(),
        'base_time': get_current_hour_string(),
        'nx': region['nx'],
        'ny': region['ny']
    }

    try:
        res = requests.get(url, params=params, timeout=3)
        data = xmltodict.parse(res.text)
        items = data['response']['body']['items']['item']

        weather = {}
        for item in items:
            category = item['category']
            value = item['obsrValue']
            if category == 'T1H':
                weather['temp'] = value
            elif category == 'REH':
                weather['humidity'] = value
            elif category == 'PTY':
                weather['pty'] = value

        return weather

    except Exception as e:
        return {"error": str(e)}

def format_weather_string(region_name, weather):
    if "error" in weather:
        return f"{region_name}: 날씨 정보 없음"

    pty = weather.get("pty", "0")
    temp = weather.get("temp", "?")

    if pty == '1':
        desc = "비"
    elif pty == '2':
        desc = "비/눈"
    elif pty == '3':
        desc = "눈"
    elif pty == '5':
        desc = "빗방울"
    elif pty == '6':
        desc = "빗방울/눈날림"
    elif pty == '7':
        desc = "눈날림"
    elif pty == '0':
        desc = "맑음"
    else:
        desc = "정보없음"

    return f"{region_name} 날씨: {desc}, {temp}℃"