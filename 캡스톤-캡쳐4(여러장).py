import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import requests
import vlc
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFrame
import sqlite3
import ctypes
import os
from PyQt5.QtCore import QTimer
import io
from PIL import Image
import threading
import time


# libvlc.dll 경로 설정 (설치된 VLC 폴더 경로)
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")

# SQLite DB 연결
def create_db():
    conn = sqlite3.connect('cctv_frames.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS frames (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        image BLOB)''')
    conn.commit()
    conn.close()

def insert_frame(image):
    conn = sqlite3.connect('cctv_frames.db')
    cursor = conn.cursor()
    timestamp = str(int(time.time()))  # timestamp
    cursor.execute("INSERT INTO frames (timestamp, image) VALUES (?, ?)",
                   (timestamp, image))
    conn.commit()
    conn.close()

def delete_old_frames():
    conn = sqlite3.connect('cctv_frames.db')
    cursor = conn.cursor()
    one_min_ago = str(int(time.time()) - 60)  # 1분 전 timestamp
    cursor.execute("DELETE FROM frames WHERE timestamp < ?", (one_min_ago,))
    conn.commit()
    conn.close()

class CCTVViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ITS CCTV Viewer with VLC")
        self.setGeometry(300, 100, 800, 600)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # VLC Player
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        # Video 프레임 (여기에 VLC 영상 들어감)
        self.video_frame = QFrame()
        self.layout.addWidget(self.video_frame)

        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

        # 버튼 5개 만들기
        self.cctv_list = self.get_cctv_list()
        for idx, cctv in enumerate(self.cctv_list[:5]):
            btn = QPushButton(f"{cctv['cctvname']}")
            btn.clicked.connect(lambda _, url=cctv['cctvurl']: self.play_stream(url))
            self.layout.addWidget(btn)

        # 타이머 설정: 1분마다 오래된 프레임 삭제
        self.timer = QTimer(self)
        self.timer.timeout.connect(delete_old_frames)
        self.timer.start(60000)  # 60,000 ms == 1분

        # 프레임 캡처용 타이머
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.capture_frame)

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

        # 기존 캡처 타이머 정지
        if self.capture_timer.isActive():
            self.capture_timer.stop()

        # VideoCapture 객체 열기
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        self.cap = cv2.VideoCapture(url)

        # 프레임 캡처 타이머 시작 (1000ms)
        self.capture_timer.start(1000)

    def capture_frame(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            ret, frame = self.cap.read()

            if ret:
                filename = os.path.abspath(f"captured_frame_{int(time.time())}.jpg")
                cv2.imwrite(filename, frame)
                print(f"{filename} 파일로 저장 완료")

                _, buffer = cv2.imencode('.jpg', frame)
                image_blob = buffer.tobytes()
                insert_frame(image_blob)
                print("프레임 캡쳐 및 DB 저장 완료")

                threading.Timer(60, self.delete_file, args=(filename,)).start()
                print(f"{filename} 60초 뒤 삭제 예약 등록 완료")
        else:
            print("VideoCapture 열려있지 않음")

    def delete_file(self, filename):
        print(f"파일 삭제 시도: {filename}")
        try:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"{filename} 삭제 완료")
            else:
                print(f"{filename} 파일 없음")
        except Exception as e:
            print(f"{filename} 삭제 중 에러: {e}")


if __name__ == "__main__":
    import time
    create_db()  # DB 생성
    app = QApplication(sys.argv)
    viewer = CCTVViewer()
    viewer.show()
    sys.exit(app.exec_())