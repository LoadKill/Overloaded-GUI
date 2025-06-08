import os
import sys
import requests
import vlc
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QApplication, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from dotenv import load_dotenv
import googlemaps
from detection_worker import DetectionWorker
from datetime import datetime

# VLC DLL 경로 추가 (Windows)
os.add_dll_directory(r"C:\Program Files\VLC")

# 환경변수 로드
load_dotenv()
api_key = os.getenv('ITS_API_KEY')
google_api_key = os.getenv('GOOGLE_API_KEY')


class WorkerSignals(QObject):
    detection_made = pyqtSignal()
    image_saved = pyqtSignal(str)


class CCTVViewer(QWidget):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals
        self.worker = None

        # 📦 메인 레이아웃 : 좌우 배치
        main_layout = QHBoxLayout(self)

        # 📌 좌측 버튼 영역
        left_layout = QVBoxLayout()

        # CCTV 리스트 가져오기
        self.cctv_list = self.get_cctv_list()

        # 시연 영상 리스트
        self.test_urls = [
            "Detection/sample/bandicam 2025-05-15 14-21-50-048.mp4",
            "Detection/sample/bandicam 2025-05-28 10-48-03-117.mp4",
            ""
        ]

        # 노선별 그룹화
        self.routes = {
            '남해선': [], '서해안선': [], '영동선': [], '경부선': [], '기타': []
        }

        for cctv in self.cctv_list:
            name = cctv['cctvname']
            if '서초' in name or '부곡' in name:
                self.routes['경부선'].append(cctv)
            elif '하동' in name:
                self.routes['남해선'].append(cctv)
            elif '횡성' in name:
                self.routes['영동선'].append(cctv)
            else:
                self.routes['기타'].append(cctv)

        # 노선 버튼 + CCTV 버튼
        for route, cctvs in self.routes.items():
            route_btn = QPushButton(route)
            route_btn.setCheckable(True)
            route_btn.setStyleSheet("font-weight: bold; background: #ddd;")
            left_layout.addWidget(route_btn)

            cctv_layout = QVBoxLayout()
            cctv_widget = QWidget()
            cctv_widget.setLayout(cctv_layout)
            cctv_widget.setVisible(False)
            left_layout.addWidget(cctv_widget)

            for cctv in cctvs:
                btn = QPushButton(f"  {cctv['cctvname']}")
                btn.setFixedHeight(36)
                btn.clicked.connect(
                    lambda _, url=cctv['cctvurl'], name=cctv['cctvname'], x=cctv['coordx'], y=cctv['coordy']:
                        self.play_stream(url, name, x, y)
                )
                cctv_layout.addWidget(btn)

            route_btn.clicked.connect(lambda checked, w=cctv_widget: w.setVisible(checked))

        # 시연 영상 버튼
        test_route_btn = QPushButton("시연 영상")
        test_route_btn.setCheckable(True)
        test_route_btn.setStyleSheet("font-weight: bold; background: #ddd;")
        left_layout.addWidget(test_route_btn)

        test_layout = QVBoxLayout()
        test_widget = QWidget()
        test_widget.setLayout(test_layout)
        test_widget.setVisible(False)
        left_layout.addWidget(test_widget)

        for i in range(1, 4):
            test_btn = QPushButton(f"  시연{i}")
            test_btn.setFixedHeight(36)
            test_btn.clicked.connect(
                lambda _, url=self.test_urls[i-1], name=f"시연{i}":
                    self.play_stream(url, name)
            )
            test_layout.addWidget(test_btn)

        test_route_btn.clicked.connect(lambda checked: test_widget.setVisible(checked))

        # 좌측 스크롤 가능하게
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(left_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(250)
        main_layout.addWidget(scroll_area)

        # 📌 가운데 영상 송출 영역
        center_layout = QVBoxLayout()
        main_layout.addLayout(center_layout)

        self.video_frame = QFrame()
        self.video_frame.setFixedSize(640, 480)
        self.video_frame.setStyleSheet("background-color: #000; border-radius: 16px;")
        center_layout.addWidget(self.video_frame)

        self.stop_button = QPushButton("영상 끄기")
        self.stop_button.setFixedHeight(40)
        self.stop_button.clicked.connect(self.stop_stream)
        center_layout.addWidget(self.stop_button)

        # 📌 우측 설명 영역
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout)

        self.video_desc_label = QLabel("영상 설명이 여기에 표시됩니다.")
        self.video_desc_label.setWordWrap(True)
        self.video_desc_label.setStyleSheet("font-size: 14px; background: #f5f5f5; padding: 10px; border-radius: 12px;")
        self.video_desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self.video_desc_label)

        # 구글맵 클라이언트
        self.gmaps = googlemaps.Client(key=google_api_key)

        # 시계+스톱워치 타이머
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_timers)
        self.clock_timer.start(1000)
        self.current_clock = datetime.now().strftime('%H:%M:%S')
        self.watch_start_time = None
        self.elapsed_str = "00:00:00"
        self.current_cctv_desc = ""

        # VLC 초기화
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.set_vlc_output()

    def set_vlc_output(self):
        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

    def get_cctv_list(self):
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=124&maxX=130&minY=33&maxY=39&getType=json"
        response = requests.get(api_url)
        data = response.json()
        target_names = [
            "하동터널(순천1 1)", "부곡1교", "횡성대교시점", "[인천2]광교방음터널(인천2외부1)",
            "광교방음터널(강릉외부1)", "광교방음터널(강릉5)", "광교방음터널(인천2)",
            "[인천2]광교방음터널(인천2외부2)", "광교방음터널(인천2 5)", "싸리재", "싸리재1", "서초"
        ]
        return [
            cctv for cctv in data['response']['data']
            if any(name in cctv['cctvname'] for name in target_names)
        ]

    def get_address_from_coord(self, lat, lng):
        try:
            result = self.gmaps.reverse_geocode((lat, lng), language='ko')
            if not result:
                return "주소 정보 없음"
            return result[0]['formatted_address']
        except Exception:
            return "주소 정보 가져오기 실패"

    def update_timers(self):
        self.current_clock = datetime.now().strftime('%H:%M:%S')
        if self.watch_start_time:
            elapsed = datetime.now() - self.watch_start_time
            h, rem = divmod(elapsed.seconds, 3600)
            m, s = divmod(rem, 60)
            self.elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"
            self.update_video_desc_label(show_time=True)
        else:
            self.elapsed_str = "00:00:00"
            self.update_video_desc_label(show_time=False)

    def update_video_desc_label(self, show_time=False):
        if show_time:
            self.video_desc_label.setText(
                f"현재 시간: {self.current_clock}\n"
                f"시청 시간: {self.elapsed_str}\n"
                f"{self.current_cctv_desc}"
            )
        else:
            self.video_desc_label.setText(self.current_cctv_desc)

    def play_stream(self, url, cctvname, coordx=None, coordy=None):
        self.watch_start_time = datetime.now()
        self.elapsed_str = "00:00:00"
        print(f"\n🎥 재생할 CCTV URL: {url}")
        self.player.stop()
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()

        if self.worker:
            self.worker.stop()
            self.worker.join()

        self.worker = DetectionWorker(url, cctvname, signal_handler=self.signals)
        self.worker.start()

        desc = f"재생중인 CCTV : {cctvname}"
        if coordx and coordy:
            try:
                address = self.get_address_from_coord(coordy, coordx)
                desc += f"\n[위치]: {address}"
            except Exception:
                desc += f"\n[위치]: 주소 정보 가져오기 실패"
        self.current_cctv_desc = desc
        self.update_video_desc_label()

    def stop_stream(self):
        self.player.stop()
        if self.worker:
            self.worker.stop()
            self.worker.join()
            self.worker = None
        print("🛑 영상 중지됨")
        self.watch_start_time = None
        self.elapsed_str = "00:00:00"
        self.current_cctv_desc = "영상이 중지되었습니다."
        self.update_video_desc_label(show_time=False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    signals = WorkerSignals()
    viewer = CCTVViewer(signals)
    viewer.show()
    sys.exit(app.exec_())

