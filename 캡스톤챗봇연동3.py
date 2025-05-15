import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import requests
import vlc
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QSizePolicy, QTextEdit, QLineEdit, QLabel, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import ctypes
import os

from PyQt5.QtWidgets import QInputDialog


# libvlc.dll 경로 설정
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")

class CCTVViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ITS CCTV Viewer with VLC")
        self.setGeometry(300, 100, 1300, 720)

        # 📌 전체 레이아웃
        self.outer_layout = QVBoxLayout()
        self.setLayout(self.outer_layout)

        # 📌 상단 타이틀바
        title_bar = QFrame()
        title_bar.setFixedHeight(60)
        title_bar.setStyleSheet("""
            background-color: #f0f0f0;
            border-radius: 16px;
        """)
        title_layout = QHBoxLayout()
        title_bar.setLayout(title_layout)

        title_label = QLabel("📺 실시간 CCTV 모니터링")
        title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #333;
        """)
        title_layout.addStretch()
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 그림자 효과
        title_shadow = QGraphicsDropShadowEffect()
        title_shadow.setBlurRadius(20)
        title_shadow.setXOffset(0)
        title_shadow.setYOffset(2)
        title_shadow.setColor(QColor(0, 0, 0, 60))
        title_bar.setGraphicsEffect(title_shadow)

        self.outer_layout.addWidget(title_bar)

        # 📌 메인 컨텐츠 영역
        self.main_layout = QHBoxLayout()
        self.outer_layout.addLayout(self.main_layout)

        # 📌 왼쪽 버튼 레이아웃
        self.button_layout = QVBoxLayout()
        self.button_layout.setSpacing(20)
        self.main_layout.addLayout(self.button_layout, 1)

        # 📌 영상 프레임
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("""
            background-color: #000;
            border-radius: 24px;
        """)
        video_shadow = QGraphicsDropShadowEffect()
        video_shadow.setBlurRadius(24)
        video_shadow.setXOffset(0)
        video_shadow.setYOffset(4)
        video_shadow.setColor(QColor(0, 0, 0, 80))
        self.video_frame.setGraphicsEffect(video_shadow)

        self.main_layout.addWidget(self.video_frame, 4)

        # 📌 챗봇 영역
        self.chatbot_frame = QFrame()
        self.chatbot_frame.setStyleSheet("""
            background-color: #f9f9f9;
            border-radius: 24px;
        """)
        self.chatbot_frame.setFixedWidth(320)
        chatbot_shadow = QGraphicsDropShadowEffect()
        chatbot_shadow.setBlurRadius(24)
        chatbot_shadow.setXOffset(0)
        chatbot_shadow.setYOffset(4)
        chatbot_shadow.setColor(QColor(0, 0, 0, 50))
        self.chatbot_frame.setGraphicsEffect(chatbot_shadow)

        self.chatbot_layout = QVBoxLayout()
        self.chatbot_frame.setLayout(self.chatbot_layout)

        # 챗봇 대화창
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 16px;
            padding: 12px;
            font-size: 14px;
            color: #333;
        """)
        self.chatbot_layout.addWidget(self.chat_display)

        # 챗봇 입력창
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("메시지를 입력하세요...")
        self.chat_input.setStyleSheet("""
            background-color: #fff;
            border: 1px solid #ccc;
            border-radius: 16px;
            padding: 12px;
            font-size: 14px;
        """)
        self.chatbot_layout.addWidget(self.chat_input)

        # 전송 버튼
        send_button = QPushButton("전송")
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #007aff;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 12px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #006de0;
            }
        """)
        send_button.clicked.connect(self.send_message)
        self.chatbot_layout.addWidget(send_button)

        self.chatbot_frame.setVisible(False)
        self.main_layout.addWidget(self.chatbot_frame, 1)

        # 📌 VLC Player 설정
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

        # 📌 CCTV 리스트 받아오기
        self.cctv_list = self.get_cctv_list()
        for idx, cctv in enumerate(self.cctv_list[:5]):

            btn = QPushButton(f"{cctv['cctvname']}")
            btn.setFixedHeight(50)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #efefef;
                    border: none;
                    border-radius: 16px;
                    padding: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    color: #333;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            btn.clicked.connect(lambda _, url=cctv['cctvurl']: self.play_stream(url))
            self.button_layout.addWidget(btn)

        # URL 영상 연결 버튼
        url_button = QPushButton("URL로 영상 재생")
        url_button.setFixedHeight(50)
        url_button.setStyleSheet("""
            QPushButton {
                background-color: #efefef;
                border: none;
                border-radius: 16px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                color: #333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        url_button.clicked.connect(self.prompt_for_video_url)
        self.button_layout.addWidget(url_button)

        # 챗봇 열기 버튼
        chatbot_button = QPushButton("챗봇 열기")
        chatbot_button.setFixedHeight(50)
        chatbot_button.setStyleSheet("""
            QPushButton {
                background-color: #007aff;
                color: white;
                border: none;
                border-radius: 16px; 
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #006de0;
            }
        """)
        chatbot_button.clicked.connect(self.toggle_chatbot)
        self.button_layout.addWidget(chatbot_button)

        # 빈 공간 Stretch
        self.button_layout.addStretch()

    def prompt_for_video_url(self):
        video_url, ok = QInputDialog.getText(self, "URL 입력", "영상 URL을 입력하세요:")
        if ok and video_url:
            self.play_stream(video_url)

    def get_cctv_list(self):
        api_key = "b226eb0b73d2424487a3928f519a9ea4"
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=126.8&maxX=127.2&minY=37.4&maxY=37.7&getType=json"
        response = requests.get(api_url)
        data = response.json()
        return data['response']['data']

    def play_stream(self, url):
        print(f"재생할 CCTV URL: {url}")
        self.player.stop()
        media = self.instance.media_new(url)
        self.player.set_media(media)
        result = self.player.play()
        print(f"play() 반환값: {result}")
        self.player.play()

    def toggle_chatbot(self):
        visible = self.chatbot_frame.isVisible()
        self.chatbot_frame.setVisible(not visible)

    def send_message(self):
        user_message = self.chat_input.text()
        if user_message.strip() == "":
            return
        self.chat_display.append(f"👤 {user_message}")
        response = f"🤖 안녕하세요!"
        self.chat_display.append(response)
        self.chat_input.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = CCTVViewer()
    viewer.show()
    sys.exit(app.exec_())
