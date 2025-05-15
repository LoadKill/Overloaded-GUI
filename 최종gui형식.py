import sys
import requests
import vlc
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QSizePolicy, QTextEdit, QLineEdit, QLabel, QGraphicsDropShadowEffect,
    QInputDialog, QTabWidget
)
import chatbot

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import ctypesf

# libvlc.dll 경로 설정 (Windows 용)
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")


# 📌 CCTVViewer 클래스 (영상 뷰어 전용)
class CCTVViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ITS CCTV Viewer")
        self.setGeometry(300, 100, 1300, 720)

        # 메인 레이아웃 (가로)
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # 📌 CCTV 버튼 레이아웃 (세로)
        button_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        # 📌 CCTV 리스트 가져오기 및 버튼 생성
        self.cctv_list = self.get_cctv_list()
        for cctv in self.cctv_list[:10]:
            btn = QPushButton(f"{cctv['cctvname']}")
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda _, url=cctv['cctvurl']: self.play_stream(url))
            button_layout.addWidget(btn)

        # 📌 오른쪽: 영상 프레임과 URL 버튼
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout)

        # 영상 프레임
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: #000; border-radius: 24px;")
        right_layout.addWidget(self.video_frame)

        # URL 재생 버튼
        self.play_button = QPushButton("URL로 영상 재생")
        self.play_button.setFixedHeight(40)
        self.play_button.clicked.connect(self.prompt_for_video_url)
        right_layout.addWidget(self.play_button)

        # 📌 VLC Player 설정
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

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
        self.player.play()


# 📌 ChatbotWidget 클래스 (챗봇 전용)
class ChatbotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("챗봇")
        self.setGeometry(300, 100, 400, 600)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # 챗봇 대화창
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # 입력창
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("메시지를 입력하세요...")
        layout.addWidget(self.chat_input)

        # 전송 버튼
        send_button = QPushButton("전송")
        send_button.clicked.connect(self.send_message)
        layout.addWidget(send_button)

    def send_message(self, image_path):
        # 챗봇 응답 가져오기
        response = chatbot(image_path)

        self.chat_display.append(f"🤖 {response}")
        self.chat_input.clear()


# 📌 메인 윈도우 (탭 구성)
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV & Chatbot 탭 화면")
        self.setGeometry(300, 100, 1300, 720)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # 탭 위젯 생성
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # CCTV 탭 추가
        self.cctv_viewer = CCTVViewer()
        self.tabs.addTab(self.cctv_viewer, "CCTV 뷰어")

        # 챗봇 탭 추가
        self.chatbot_view = ChatbotWidget()
        self.tabs.addTab(self.chatbot_view, "챗봇")


# 📌 실행
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
