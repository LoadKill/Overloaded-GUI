import sys
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPropertyAnimation
from datetime import datetime
import itertools

class TrafficIncidentBanner(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("돌발교통정보 배너")
        self.setGeometry(100, 100, 1200, 50)
        self.setStyleSheet("background-color: #222; color: white;")

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 5, 10, 5)

        # 날짜 라벨
        self.date_label = QLabel()
        self.date_label.setStyleSheet("font-size: 16px; color: #ccc;")
        top_layout.addWidget(self.date_label)

        # 돌발정보 라벨
        self.incident_label = QLabel("돌발교통정보 로딩 중...")
        self.incident_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        top_layout.addWidget(self.incident_label)

        # 투명도 효과 적용
        self.opacity_effect = QGraphicsOpacityEffect()
        self.incident_label.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        self.setLayout(main_layout)

        # 30분마다 데이터 갱신
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_incident_data)
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
        self.load_incident_data()

    def update_date(self):
        current_date = QDateTime.currentDateTime().toString("yyyy. M. d. AP h:mm")
        self.date_label.setText(current_date)

    def load_incident_data(self):
        try:
            api_key = "8637559074094717b79ee9d5cbcabb0c"
            url = f"https://openapi.its.go.kr:9443/eventInfo?apiKey={api_key}&type=all&eventType=all&minX=124&maxX=132&minY=33&maxY=39&getType=json"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            events = data.get("body", {}).get("items", [])
            filtered_texts = []

            for event in events:
                road_name = event.get("roadName", "정보없음")
                if road_name not in ["남해선", "서해안선", "영동선", "경부선"]:
                    continue

                event_type = event.get("eventType", "정보없음")
                message = event.get("message", "")
                start_date_raw = event.get("startDate", "")

                if start_date_raw:
                    start_date = datetime.strptime(start_date_raw, "%Y%m%d%H%M%S")
                    start_date_str = f"{start_date.month}월{start_date.day}일 {start_date.strftime('%H:%M')}"
                else:
                    start_date_str = "시간없음"

                text = f"[{road_name}][{event_type}] {message} ({start_date_str})"
                filtered_texts.append(text)

            if filtered_texts:
                self.incident_texts = itertools.cycle(filtered_texts)
            else:
                self.incident_texts = itertools.cycle(["현재 돌발교통정보 없음"])

        except Exception as e:
            self.incident_texts = itertools.cycle([f"API 오류: {str(e)}"])

    def fade_out(self):
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.change_text)
        self.animation.start()

    def change_text(self):
        self.incident_label.setText(next(self.incident_texts))
        self.fade_in()

    def fade_in(self):
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrafficIncidentBanner()
    window.show()
    sys.exit(app.exec_())
