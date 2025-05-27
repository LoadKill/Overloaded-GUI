import sqlite3
from datetime import datetime
import cv2
import os
import numpy as np

def init_db():
    # 항상 Detection 폴더 내 DB로 고정
    db_path = os.path.join(os.path.dirname(__file__), "illegal_vehicle.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS illegal_vehicles (
        track_id INTEGER PRIMARY KEY,
        timestamp TEXT,
        class TEXT,
        x1 INTEGER, y1 INTEGER, x2 INTEGER, y2 INTEGER,
        image_path TEXT,
        cctvname TEXT,
        analysis_result TEXT
    )""")
    conn.commit()

    return conn, cursor



def is_already_saved(cursor, track_id):
    cursor.execute("SELECT 1 FROM illegal_vehicles WHERE track_id=?", (track_id,))
    return cursor.fetchone() is not None


def save_illegal_vehicle(frame, box, track_id, cursor, conn, cctvname=""):
    x1, y1, x2, y2, _ = map(int, box)
    h, w = frame.shape[:2]

    # (선택) margin 조금 넓히기
    margin = 0.1
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - bw * margin))
    y1 = max(0, int(y1 - bh * margin))
    x2 = min(w, int(x2 + bw * margin))
    y2 = min(h, int(y2 + bh * margin))

    roi = frame[y1:y2, x1:x2]
    
    # --- 슈퍼레졸루션 적용 (OpenCV dnn_superres 예시) ---
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel('ESPCN_x4.pb')
    sr.setModel('espcn', 4)
    roi = sr.upsample(roi)
    # ----------------------------------------------


    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")

    folder_path = os.path.join("Detection", "saved_illegal_espcn", date_str)
    os.makedirs(folder_path, exist_ok=True)

    filename = f"illegal_{track_id}_{time_str}.jpg"
    save_path = os.path.join(folder_path, filename)
    result = cv2.imwrite(save_path, roi, [cv2.IMWRITE_JPEG_QUALITY, 95])

    if result:
        print(f"[✅ 저장 성공] {save_path}")
    else:
        print(f"[❌ 저장 실패] {save_path}")

    db_path = os.path.join("Detection", "saved_illegal", date_str, filename)

    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")


    cursor.execute("""
        INSERT INTO illegal_vehicles (track_id, timestamp, class, x1, y1, x2, y2, image_path, cctvname, analysis_result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (track_id, timestamp, 'illegal', x1, y1, x2, y2, db_path, cctvname, None))
    conn.commit()

    print(f"[✅ 저장 완료] {db_path}")