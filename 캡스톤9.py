import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import requests
import vlc
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFrame
import ctypes
import os

# libvlc.dll 경로 설정 (설치된 VLC 폴더 경로)
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = CCTVViewer()
    viewer.show()
    sys.exit(app.exec_())