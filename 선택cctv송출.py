import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import requests
import vlc
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSizePolicy
import ctypes
import os

# libvlc.dll 경로 설정
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")

class CCTVViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ITS CCTV Viewer with VLC")
        self.setGeometry(300, 100, 1000, 600)

        # 📌 전체 레이아웃: 좌우로 나누기
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        # 📌 왼쪽 버튼 레이아웃 (세로)
        self.button_layout = QVBoxLayout()
        self.button_layout.setSpacing(25)  # 버튼 간격 넓힘
        self.main_layout.addLayout(self.button_layout, 1)

        # 📌 오른쪽 VLC 영상 프레임
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black; border-radius: 20px;")
        self.main_layout.addWidget(self.video_frame, 4)

        # VLC Player
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

        # 📌 CCTV 리스트 받아와서 버튼 5개 생성
        self.cctv_list = self.get_cctv_list()
        for idx, cctv in enumerate(self.cctv_list[:5]):
            btn = QPushButton(f"{cctv['cctvname']}")
            btn.setFixedHeight(50)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            btn.setStyleSheet("""
                QPushButton {
                    background-color: #d0d0d0;
                    border: none;
                    border-radius: 12px;
                    padding: 10px;
                    font-size: 16px;
                    font-weight: bold;
                    color: #333;
                }
                QPushButton:hover {
                    background-color: #c0c0c0;
                }
                QPushButton:pressed {
                    background-color: #b0b0b0;
                }
            """)

            btn.clicked.connect(lambda _, url=cctv['cctvurl']: self.play_stream(url))
            self.button_layout.addWidget(btn)

        # 📌 추가 버튼 3개 (시연1, 시연2, 시연3)
        for i in range(1, 4):
            test_btn = QPushButton(f"시연{i}")
            test_btn.setFixedHeight(50)
            test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            test_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffd966;
                    border: none;
                    border-radius: 12px;
                    padding: 10px;
                    font-size: 16px;
                    font-weight: bold;
                    color: #333;
                }
                QPushButton:hover {
                    background-color: #f4c542;
                }
                QPushButton:pressed {
                    background-color: #d9a300;
                }
            """)

            # 빈화면 재생 함수 연결 (None 스트림)
            test_btn.clicked.connect(lambda _, url="": self.play_stream(url))
            self.button_layout.addWidget(test_btn)

        # 빈 공간 Stretch 추가
        self.button_layout.addStretch()

    def get_cctv_list(self):
        api_key = "b226eb0b73d2424487a3928f519a9ea4"
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=124&maxX=130&minY=33&maxY=39&getType=json"
        response = requests.get(api_url)
        data = response.json()

        # 내가 보고싶은 CCTV 이름 리스트
        target_names = [
            "하동터널(순천1 1)", "부곡1교", "횡성대교시점", "[인천2]광교방음터널(인천2외부1)",
            "광교방음터널(강릉외부1)", "광교방음터널(강릉5)", "광교방음터널(인천2)",
            "[인천2]광교방음터널(인천2외부2)", "광교방음터널(인천2 5)", "싸리재", "싸리재1", "서초"
        ]

        # target_names 중 이름이 포함된 CCTV만 필터링
        cctv_list = [
            cctv for cctv in data['response']['data']
            if any(name in cctv['cctvname'] for name in target_names)
        ]

        return cctv_list

    def play_stream(self, url):
        print(f"재생할 CCTV URL: {url}")
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = CCTVViewer()
    viewer.show()
    sys.exit(app.exec_())
