import requests
from datetime import datetime


def get_weather(stn):
    api_url = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm2.php"
    params = {
        "stn": stn,
        "authKey": "5SobbpxASCSqG26cQOgkpw"
    }

    response = requests.get(api_url, params=params)
    if response.status_code != 200:
        print(f"관측소 {stn} 데이터 요청 실패: 상태코드 {response.status_code}")
        return

    text = response.text.strip()
    # 데이터가 텍스트형태로 여러 줄로 옴 (예: 시간, 기온, 강수량, 습도 등)
    # 각 줄을 분리 후 필요한 정보만 뽑아 출력

    lines = text.splitlines()
    for line in lines:
        if line.startswith("#") or not line.strip():
            continue

        parts = line.split()
        if len(parts) < 4:
            continue


        time_str = parts[0]


        # 시간 가공
        year = time_str[0:4]
        month = time_str[4:6]
        day = time_str[6:8]
        hour = time_str[8:10]
        minute = time_str[10:12]

        temp = parts[2]
        rain = parts[3]
        humidity = parts[13] if len(parts) > 13 else "-9"

        # -9는 결측값! -9가 나오면 출력하지 않게 설정
        if temp == "-9" or rain == "-9" or humidity == "-9":
            continue

        print(f"[관측소 {stn}] 시간: {month}월{day}일 {hour}시{minute}분, 기온: {temp}°C, 강수량: {rain}mm, 습도: {humidity}%")


if __name__ == "__main__":
    region_stations = {
        "전라남도": [156, 157],
        "경기도": [112, 115, 116],
        "충청남도": [133, 134],
        "경상북도": [143, 144],
        "강원도": [105, 106],
        "서울": [108, 109],
        "대전": [131],
        "대구": [138],
        "부산": [159]
    }                      #"남해선", "서해안선", "영동선", "경부선"이 지나가는 지역

    for region, stations in region_stations.items():
        print(f"\n== {region} 지역 기상정보 ==")
        for stn in stations:
            get_weather(stn)
