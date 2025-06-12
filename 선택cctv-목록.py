import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import requests
import vlc
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSizePolicy
import ctypes
import os

# libvlc.dll 경로 설정 (경로 확인하고 바꾸기!!!)
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")


class CCTVViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("노선별 CCTV & 시연 영상 뷰어")
        self.setGeometry(300, 100, 1200, 700)

        # 📌 전체 레이아웃: 좌우로 나누기
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        # 📌 왼쪽 버튼 레이아웃 (세로)
        self.button_layout = QVBoxLayout()
        self.button_layout.setSpacing(15)
        self.main_layout.addLayout(self.button_layout, 1)

        # 📌 오른쪽 VLC 영상 프레임
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black; border-radius: 20px;")
        self.main_layout.addWidget(self.video_frame, 4)

        # 📌 VLC Player
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

        # 📌 노선별 CCTV 리스트 가져오기
        self.route_dict = self.get_route_cctv_list()

        # 📌 버튼 관리용 딕셔너리
        self.route_buttons = {}
        self.cctv_buttons = {}

        for route_name in self.route_dict.keys():
            # 노선 버튼 생성
            route_btn = QPushButton(route_name)
            route_btn.setFixedHeight(50)
            route_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            route_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a3c2f2;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    color: #333;
                }
                QPushButton:hover {
                    background-color: #80b0e0;
                }
                QPushButton:pressed {
                    background-color: #6197d3;
                }
            """)
            route_btn.clicked.connect(lambda _, name=route_name: self.toggle_cctv_buttons(name))
            self.button_layout.addWidget(route_btn)

            # 버튼 레퍼런스 저장
            self.route_buttons[route_name] = route_btn
            self.cctv_buttons[route_name] = []

        # 📌 시연 영상 URL 리스트
        self.test_urls = [
            "",  # 시연1 영상 URL 추후 삽입 가능
            "",  # 시연2
            ""   # 시연3
        ]

        # 📌 시연 버튼 3개 생성
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
            test_btn.clicked.connect(lambda _, url=self.test_urls[i-1]: self.play_stream(url))
            self.button_layout.addWidget(test_btn)

        # 📌 빈공간 stretch
        self.button_layout.addStretch()

    def get_route_cctv_list(self): # CCTV리스트 가지고 와서 도로별로 나눠주는 함수
        api_key = "b226eb0b73d2424487a3928f519a9ea4"
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=124&maxX=130&minY=33&maxY=39&getType=json"
        response = requests.get(api_url)
        data = response.json()
        #ITS에서 제공하는 공공cCtv api서버에 접속, api key넣고 좌표 범위 설정해서 cctv정보를 json형식으로 받아오는 거

        cctv_data = data['response']['data']

        route_dict = {
            "남해선": [],
            "서해안선": [],
            "영동선": [],
            "경부선": []
        } #CCTV를 각 도로 노선 이름으로 묶어서 저장

        for cctv in cctv_data:
            name = cctv['cctvname']
            # 노선별 CCTV 분류
            if "하동터널" in name:
                route_dict["남해선"].append(cctv)
            elif "부곡1교" in name:
                route_dict["서해안선"].append(cctv)
            elif ("광교" in name and "상현IC" not in name) or "횡성대교" in name or "싸리재" in name:
                route_dict["영동선"].append(cctv)
            elif "서초" in name or "석적교" in name:
                route_dict["경부선"].append(cctv) #이름에 포함된 키워드로 분류

        return route_dict

    def toggle_cctv_buttons(self, route_name):
        # 이미 버튼이 표시돼 있으면 제거
        if self.cctv_buttons[route_name]:
            for btn in self.cctv_buttons[route_name]:
                self.button_layout.removeWidget(btn)
                btn.deleteLater()
            self.cctv_buttons[route_name] = []
        else:
            # 새로 버튼 추가
            for cctv in self.route_dict[route_name]:
                btn = QPushButton("  └ " + cctv['cctvname'])
                btn.setFixedHeight(40)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #d9d9d9;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                        color: #333;
                        text-align: left;
                        padding-left: 20px;
                    }
                    QPushButton:hover {
                        background-color: #bcbcbc;
                    }
                    QPushButton:pressed {
                        background-color: #999999;
                    }
                """)
                btn.clicked.connect(lambda _, url=cctv['cctvurl']: self.play_stream(url))
                route_index = self.button_layout.indexOf(self.route_buttons[route_name])
                self.button_layout.insertWidget(route_index + 1, btn)
                self.cctv_buttons[route_name].append(btn)

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
