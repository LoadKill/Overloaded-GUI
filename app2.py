import sys
import requests
import vlc
import os
import sqlite3
import threading
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QTextEdit, QLabel, QInputDialog, QTabWidget, QListWidget,
    QListWidgetItem, QFileDialog, QMessageBox, QScrollArea, 
)


from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QIcon
from dotenv import load_dotenv
from chatbot import analyze_image
from Detection.detector import load_model, detect_vehicles
from Detection.tracker import init_tracker, update_tracks
from Detection.db import save_illegal_vehicle, init_db, is_already_saved
from Detection.utils import match_with_track

os.add_dll_directory(r"C:\Program Files\VLC") # vlc경로 확인해서 고쳐주세요!!
load_dotenv()
api_key = os.getenv('ITS_API_KEY')


class WorkerSignals(QObject):
    detection_made = pyqtSignal()

class DetectionWorker(threading.Thread):
    def __init__(self, stream_url, cctvname, signal_handler=None):
        super().__init__()
        self.stream_url = stream_url
        self.cctvname = cctvname
        self.running = True
        self.model = load_model("Detection/model/yolov8_n.pt").to("cuda")
        self.tracker = init_tracker()
        self.signals = signal_handler  # 🔹 새로 추가된 시그널 핸들러

    def run(self):
        conn, cursor = init_db()
        cap = cv2.VideoCapture(self.stream_url)
        try:
            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    continue

                detections, illegal_boxes = detect_vehicles(self.model, frame, conf_threshold=0.5)

                tracks = update_tracks(self.tracker, detections)

                for box in illegal_boxes:
                    matched_id = match_with_track(box, tracks)
                    if matched_id and not is_already_saved(cursor, matched_id):
                        save_illegal_vehicle(frame, box, matched_id, cursor, conn, self.cctvname)

                        # 🔹 탐지되었을 때 시그널 발신
                        if self.signals:
                            self.signals.detection_made.emit()

        finally:
            cap.release()
            conn.close()

    def stop(self):
        self.running = False



class CCTVViewer(QWidget):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals
        self.worker = None

        # 버튼 레이아웃 (외부에서 접근하려고 속성으로 선언)
        self.button_layout = QVBoxLayout()

        self.cctv_list = self.get_cctv_list()
        for cctv in self.cctv_list[:10]:
            btn = QPushButton(f"{cctv['cctvname']}")
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda _, url=cctv['cctvurl'], name=cctv['cctvname']: self.play_stream(url, name))
            self.button_layout.addWidget(btn)

        # 영상 표시 프레임
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: #000; border-radius: 24px;")

        # 영상 재생 버튼
        self.play_button = QPushButton("URL로 영상 재생")
        self.play_button.setFixedHeight(40)
        self.play_button.clicked.connect(self.prompt_for_video_url)

        # ✅ 영상 끄기 버튼
        self.stop_button = QPushButton("영상 끄기")
        self.stop_button.setFixedHeight(40)
        self.stop_button.clicked.connect(self.stop_stream)

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
            self.play_stream(video_url, "사용자입력")

    def get_cctv_list(self):
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=126.8&maxX=126.9&minY=36.7&maxY=37.0&getType=json"
        response = requests.get(api_url)
        data = response.json()
        return data['response']['data']

    def play_stream(self, url, cctvname):
        print(f"\n🎥 재생할 CCTV URL: {url}")
        self.player.stop()
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()

        # ✅ 이전 스레드가 존재하면 안전하게 종료
        if self.worker:
            self.worker.stop()
            self.worker.join()  # <- 완전히 종료될 때까지 기다림

        # ✅ 새로운 탐지 스레드 시작
        self.worker = DetectionWorker(url, cctvname, signal_handler=self.signals)
        self.worker.start()


    def stop_stream(self):
        self.player.stop()
        if self.worker:
            self.worker.stop()
            self.worker.join()
            self.worker = None
        print("🛑 영상 중지됨")


class ImageListItem(QWidget):
    def __init__(self, timestamp, path, cctvname, parent):
        super().__init__()
        self.parent_widget = parent
        self.image_path = path
        self.is_expanded = False
        self.analysis_result = None
        self.analysis_running = False

        self.setFixedWidth(400)

        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        # 썸네일 + 제목
        top_row = QHBoxLayout()
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(60, 40)
        self.thumbnail.setScaledContents(True)
        if os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path).scaled(60, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail.setPixmap(pixmap)

        self.header = QLabel(f"[{cctvname}] {timestamp}")
        self.header.setWordWrap(True)
        self.header.setFixedWidth(320)
        self.header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.header.setStyleSheet("padding: 5px; background: transparent;")
        self.header.mousePressEvent = lambda event: self.toggle_expand()

        top_row.addWidget(self.thumbnail)
        top_row.addWidget(self.header)
        self.main_layout.addLayout(top_row)

        # 요약
        self.preview_label = QLabel("⏳ 분석 대기 중...")
        self.preview_label.setStyleSheet("color: gray; font-size: 12px; margin-left: 64px;")
        self.main_layout.addWidget(self.preview_label)

        # 확장 프레임
        self.expand_frame = QFrame()
        self.expand_frame.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ccc;")
        self.expand_frame.setVisible(False)
        expand_layout = QVBoxLayout()
        self.expand_frame.setLayout(expand_layout)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedHeight(350)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)

        self.close_button = QPushButton("닫기")
        self.close_button.clicked.connect(self.collapse)

        expand_layout.addWidget(self.image_label)
        expand_layout.addWidget(self.chat_display)
        expand_layout.addWidget(self.close_button)

        self.main_layout.addWidget(self.expand_frame)

    def start_analysis(self):
        if self.analysis_running or self.analysis_result:
            return
        
        conn, cursor = init_db()

        try:
            cursor.execute("SELECT analysis_result FROM illegal_vehicles WHERE image_path = ?", (self.image_path,))
            row = cursor.fetchone()
            if row and row[0]:
                self.analysis_result = row[0]
                self.preview_label.setText(row[0].strip().splitlines()[0])
                return  # 🔹 이미 분석된 결과가 있으므로 여기서 종료
        finally:
            conn.close()

        self.analysis_running = True
        self.preview_label.setText("🧠 분석 중...")

        result = analyze_image(self.image_path)
        print(result)
        self.analysis_result = result
        self.analysis_running = False
        first_line = result.strip().splitlines()[0] if result else "(결과 없음)"
        self.preview_label.setText(first_line)

        conn, cursor = init_db()
        try:
            cursor.execute("UPDATE illegal_vehicles SET analysis_result = ? WHERE image_path = ?", (result, self.image_path))
            conn.commit()
        finally:
            conn.close()


    def toggle_expand(self):
        self.parent_widget.collapse_all_except(self)

        if not self.is_expanded:
            if os.path.exists(self.image_path):
                pixmap = QPixmap(self.image_path).scaled(400, 250, Qt.KeepAspectRatio)
                self.image_label.setPixmap(pixmap)
            if self.analysis_result:
                self.chat_display.setText(f"분석 결과:\n{self.analysis_result}")
            else:
                self.chat_display.setText("아직 분석되지 않았습니다.")
            self.expand_frame.setVisible(True)
            self.is_expanded = True
        else:
            self.collapse()

    def collapse(self):
        self.expand_frame.setVisible(False)
        self.is_expanded = False




class ImageBrowserWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(500)
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        content = QWidget()
        self.vbox = QVBoxLayout(content)
        content.setLayout(self.vbox)
        scroll.setWidget(content)

        self.items = []
        self.image_paths = set()
        self.analysis_queue = []
        self.analysis_index = 0
        self.processing = False

        self.populate_image_items()

    def populate_image_items(self):
        conn, cursor = init_db()
        try:
            cursor.execute("SELECT timestamp, image_path, cctvname FROM illegal_vehicles ORDER BY timestamp DESC")
            for timestamp, path, cctvname in cursor.fetchall():
                if not os.path.exists(path):
                    continue
                item = ImageListItem(timestamp, path, cctvname, self)
                #item.setFixedHeight(100)
                self.vbox.addWidget(item)
                self.items.append(item)
                self.analysis_queue.append(item)
            self.vbox.addStretch()
            self.run_next_analysis()
        finally:
            conn.close()

    def add_new_image_item(self, timestamp, path, cctvname, to_top=True):
        """새 이미지 감지(또는 DB에 추가)시 리스트에 동적으로 추가"""
        if path in self.image_paths:    # 중복 방지
            return
        item = ImageListItem(timestamp, path, cctvname, self)
        if to_top:
            self.vbox.insertWidget(0, item)      # 최신 이미지는 맨 위에 추가
            self.items.insert(0, item)
        else:
            self.vbox.addWidget(item)
            self.items.append(item)
        self.image_paths.add(path)               # 중복 방지용 집합에 경로 등록
        self.analysis_queue.append(item)
        self.run_next_analysis()                 # 필요시 바로 분석


    def handle_new_detection(self):
        """새 탐지 발생(시그널)시 DB에서 가장 최근 이미지 하나만 추가"""
        conn, cursor = init_db()
        try:
            cursor.execute("SELECT timestamp, image_path, cctvname FROM illegal_vehicles ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                timestamp, path, cctvname = row
                if os.path.exists(path):
                    self.add_new_image_item(timestamp, path, cctvname)
        finally:
            conn.close()


    def run_next_analysis(self):
        if self.processing or self.analysis_index >= len(self.analysis_queue):
            return

        self.processing = True
        item = self.analysis_queue[self.analysis_index]

        def process():
            item.start_analysis()
            self.analysis_index += 1
            self.processing = False
            QTimer.singleShot(100, self.run_next_analysis)

        QTimer.singleShot(10, process)

    def collapse_all_except(self, current_item):
        for item in self.items:
            if item != current_item and item.is_expanded:
                item.expand_frame.setVisible(False)
                item.is_expanded = False



class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV 모니터링 + 챗봇")
        self.setGeometry(300, 100, 1600, 800)

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        self.signals = WorkerSignals()

        # 1️⃣ 왼쪽: CCTV 버튼 리스트
        self.cctv_viewer = CCTVViewer(signals=self.signals)
        main_layout.addLayout(self.cctv_viewer.button_layout, 2)

        # 2️⃣ 중앙: VLC 영상 영역
        video_layout = QVBoxLayout()
        video_layout.addWidget(self.cctv_viewer.video_frame, 8)
        video_layout.addWidget(self.cctv_viewer.play_button, 1)
        video_layout.addWidget(self.cctv_viewer.stop_button, 1)
        main_layout.addLayout(video_layout, 5)

        # 3️⃣ 오른쪽: 이미지 리스트 (탐지 결과)
        self.image_browser = ImageBrowserWidget()
        self.signals.detection_made.connect(self.image_browser.handle_new_detection)
        main_layout.addWidget(self.image_browser, 5)

    def closeEvent(self, event):
        if self.cctv_viewer.worker:
            self.cctv_viewer.worker.stop()
            self.cctv_viewer.worker.join()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())



