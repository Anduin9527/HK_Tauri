import cv2
import time
import threading
import numpy as np


class Camera:
    def __init__(
        self, rtsp_url=0, camera_id=0
    ):  # Default to webcam 0 for testing if no URL
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.cap = None
        self.connected = False
        self._lock = threading.Lock()

        # Reconnection control
        self.last_reconnect_time = 0
        self.reconnect_interval = 5.0  # seconds

        # Attempt initial connection
        self.connect()

    def connect(self):
        with self._lock:
            now = time.time()
            if now - self.last_reconnect_time < self.reconnect_interval:
                return

            self.last_reconnect_time = now

            if self.cap is not None:
                self.cap.release()

            print(
                f"[{self.camera_id}] Connecting to camera source: {self.rtsp_url} ..."
            )
            try:
                # If URL is an integer (for local webcam) or string
                if isinstance(self.rtsp_url, str) and self.rtsp_url.isdigit():
                    src = int(self.rtsp_url)
                else:
                    src = self.rtsp_url

                self.cap = cv2.VideoCapture(src)

                if self.cap.isOpened():
                    self.connected = True
                    print(f"[{self.camera_id}] Camera connected successfully.")
                else:
                    self.connected = False
                    print(f"[{self.camera_id}] Failed to connect to camera.")
            except Exception as e:
                print(f"[{self.camera_id}] Connection error: {e}")
                self.connected = False

    def set_source(self, new_url):
        self.rtsp_url = new_url
        self.last_reconnect_time = 0  # Force immediate retry
        self.connect()

    def get_frame(self):
        if not self.connected:
            self.connect()
            if not self.connected:
                return self._get_test_pattern("No Signal")

        ret, frame = self.cap.read()
        if not ret:
            self.connected = False
            return self._get_test_pattern("Connection Lost")

        return frame

    def _get_test_pattern(self, text):
        # Create a dynamic pattern based on time and camera ID
        h, w = 480, 640
        canvas = np.zeros((h, w, 3), np.uint8)

        # Moving box to show liveness
        t = time.time()
        x = int((np.sin(t) + 1) * 200) + 50
        y = int((np.cos(t) + 1) * 100) + 50

        # Different color per camera ID
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        color = colors[self.camera_id % len(colors)]

        cv2.rectangle(canvas, (x, y), (x + 50, y + 50), color, -1)

        # Text info
        cv2.putText(
            canvas,
            f"CAM {self.camera_id}",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            canvas, text, (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1
        )
        cv2.putText(
            canvas,
            time.strftime("%H:%M:%S"),
            (30, 450),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (150, 150, 150),
            1,
        )
        return canvas

    def is_connected(self):
        return self.connected

    def release(self):
        if self.cap:
            self.cap.release()
