import requests
from datetime import datetime
import time

def load_incident_data():
    api_key = "8637559074094717b79ee9d5cbcabb0c"
    url = f"https://openapi.its.go.kr:9443/eventInfo?apiKey={api_key}&type=all&eventType=all&minX=124&maxX=132&minY=33&maxY=39&getType=json"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        events = data.get("body", {}).get("items", [])
        if not events:
            print("현재 등록된 돌발교통정보가 없습니다.")
            return

        target_roads = ["남해선", "서해안선", "영동선", "경부선"]

        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 실시간 돌발교통정보 (지정 노선만)\n")
        for event in events:
            road_name = event.get('roadName', '정보없음')

            if road_name not in target_roads:
                continue

            event_type = event.get('eventType', '정보없음')
            message = event.get('message', '정보없음')
            start_date_raw = event.get('startDate', '')

            # 발생시간 포맷 가공
            if start_date_raw:
                start_date = datetime.strptime(start_date_raw, "%Y%m%d%H%M%S")
                start_date_str = f"{start_date.month}월{start_date.day}일 {start_date.hour:02d}:{start_date.minute:02d}"
            else:
                start_date_str = "정보없음"

            print(f"[{road_name}][{event_type}] {message} ({start_date_str})")

    except Exception as e:
        print(f"API 호출 실패 또는 데이터 처리 오류:\n{str(e)}")

if __name__ == "__main__":
    while True:
        load_incident_data()
        print("\n다음 갱신까지 30분 대기...\n")
        time.sleep(1800)  # 1800초 = 30분


