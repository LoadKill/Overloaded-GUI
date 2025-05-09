import sys
import requests
import vlc
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QFrame, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class TrafficCCTVChatUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📹 과적차량 검출 관제 시스템")
        self.setGeometry(200, 100, 1400, 750)
        self.setStyleSheet("background-color: #1c1c1e; color: #f2f2f7;")

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # 📌 좌측 CCTV 버튼 리스트
        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        main_layout.addLayout(left_layout, 1)

        self.cctv_list = self.get_cctv_list()
        for cctv in self.cctv_list[:5]:
            btn = QPushButton(f"{cctv['cctvname']}")
            btn.setFixedHeight(60)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: none;
                    border-radius: 14px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #3a3a3c;
                }
            """)
            btn.clicked.connect(lambda _, url=cctv['cctvurl']: self.play_stream(url))
            left_layout.addWidget(btn)
        left_layout.addStretch()

        # 📌 중앙 챗봇 대화영역
        center_layout = QVBoxLayout()
        main_layout.addLayout(center_layout, 2)

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet("""
            QTextEdit {
                background-color: #2c2c2e;
                border: none;
                border-radius: 16px;
                padding: 12px;
                font-size: 15px;
                color: #f2f2f7;
            }
        """)
        center_layout.addWidget(self.chat_area)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3c;
                border: none;
                border-radius: 14px;
                padding: 12px;
                font-size: 15px;
                color: #f2f2f7;
            }
        """)
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("전송")
        self.send_button.setFixedHeight(45)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0a84ff;
                color: #fff;
                border: none;
                border-radius: 14px;
                font-size: 15px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0066cc;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        center_layout.addLayout(input_layout)

        # 📌 우측 CCTV 영상 영역
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black; border-radius: 20px;")
        main_layout.addWidget(self.video_frame, 3)

        # VLC Player
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

    def get_cctv_list(self):
        api_key = "b226eb0b73d2424487a3928f519a9ea4"
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=126.8&maxX=127.2&minY=37.4&maxY=37.7&getType=json"
        response = requests.get(api_url)
        data = response.json()
        return data['response']['data']

    def play_stream(self, url):
        print(f"재생할 CCTV URL: {url}")
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()

    def send_message(self):
        msg = self.input_field.text()
        if msg:
            self.chat_area.append(f"👤 사용자: {msg}")
            self.chat_area.append(f"🤖 챗봇: 메시지를 확인했어요.")
            self.input_field.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrafficCCTVChatUI()
    window.show()
    sys.exit(app.exec_())
