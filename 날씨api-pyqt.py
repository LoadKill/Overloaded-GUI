import sys
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPropertyAnimation
from datetime import datetime
import itertools

class WeatherBanner(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("날씨정보 배너")
        self.setGeometry(100, 100, 1200, 50)
        self.setStyleSheet("background-color: #222; color: white;")

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 5, 10, 5)

        # 날짜 라벨
        self.date_label = QLabel()
        self.date_label.setStyleSheet("font-size: 16px; color: #ccc;")
        top_layout.addWidget(self.date_label)

        # 날씨정보 라벨
        self.weather_label = QLabel("날씨정보 로딩 중...")
        self.weather_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        top_layout.addWidget(self.weather_label)

        # 투명도 효과 적용
        self.opacity_effect = QGraphicsOpacityEffect()
        self.weather_label.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        self.setLayout(main_layout)

        # 30분마다 데이터 갱신
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_weather_data)
        self.refresh_timer.start(30 * 60 * 1000)

        # 8초마다 텍스트 변경
        self.display_timer = QTimer(self)
        self.display_timer.timeout.connect(self.fade_out)
        self.display_timer.start(8000)

        # 날짜 갱신
        self.date_timer = QTimer(self)
        self.date_timer.timeout.connect(self.update_date)
        self.date_timer.start(1000)

        self.update_date()
        self.load_weather_data()

    def update_date(self):
        current_date = QDateTime.currentDateTime().toString("yyyy. M. d. AP h:mm")
        self.date_label.setText(current_date)

    def load_weather_data(self):
        try:
            region_stations = {
                "전남": [156, 157],
                "경기": [112, 115, 116],
                "충남": [133, 134],
                "경북": [143, 144],
                "강원": [105, 106],
                "서울": [108],
                "대전": [131],
                "대구": [138],
                "부산": [159] #대충 남해선, 서해안선, 영동선, 경부서" 지나가는 곳
            }

            api_url = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm2.php"
            api_key = "5SobbpxASCSqG26cQOgkpw"

            weather_texts = []

            for region, stations in region_stations.items():
                for stn in stations:
                    params = {"stn": stn, "authKey": api_key}
                    response = requests.get(api_url, params=params)
                    if response.status_code != 200:
                        continue

                    text = response.text.strip()
                    lines = text.splitlines()
                    for line in lines:
                        if line.startswith("#") or not line.strip():
                            continue

                        parts = line.split()
                        if len(parts) < 4:
                            continue

                        time_str = parts[0]
                        temp = parts[2]
                        rain = parts[3]
                        humidity = parts[13] if len(parts) > 13 else "-9"

                        # 결측값 처리
                        if temp == "-9" or rain == "-9" or humidity == "-9":
                            continue

                        year, month, day = time_str[0:4], time_str[4:6], time_str[6:8]
                        hour, minute = time_str[8:10], time_str[10:12]

                        formatted = f"[{region}] {month}월{day}일 {hour}:{minute} | {temp}°C / 강수량 {rain}mm / 습도 {humidity}%"
                        weather_texts.append(formatted)

                        # 관측소별 최신 데이터 1개만
                        break

            if weather_texts:
                self.weather_texts = itertools.cycle(weather_texts)
            else:
                self.weather_texts = itertools.cycle(["현재 날씨정보 없음"])

        except Exception as e:
            self.weather_texts = itertools.cycle([f"API 오류: {str(e)}"])

    def fade_out(self):
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.change_text)
        self.animation.start()

    def change_text(self):
        self.weather_label.setText(next(self.weather_texts))
        self.fade_in()

    def fade_in(self):
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeatherBanner()
    window.show()
    sys.exit(app.exec_())
