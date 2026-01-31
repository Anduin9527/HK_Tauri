import cv2
import time
import threading


class Camera:
    def __init__(self, rtsp_url=0):  # Default to webcam 0 for testing if no URL
        self.rtsp_url = rtsp_url
        self.cap = None
        self.connected = False
        self._lock = threading.Lock()

        # Attempt initial connection
        self.connect()

    def connect(self):
        with self._lock:
            if self.cap is not None:
                self.cap.release()

            print(f"Connecting to camera source: {self.rtsp_url} ...")
            self.cap = cv2.VideoCapture(self.rtsp_url)

            if self.cap.isOpened():
                self.connected = True
                print("Camera connected successfully.")
            else:
                self.connected = False
                print("Failed to connect to camera.")

    def set_source(self, new_url):
        self.rtsp_url = new_url
        self.connect()

    def get_frame(self):
        if not self.connected:
            # Try reconnect logic periodically?
            # For simplicity, we just return a blank or retry here
            self.connect()
            if not self.connected:
                return self._get_blank_frame("No Signal")

        ret, frame = self.cap.read()
        if not ret:
            self.connected = False
            return self._get_blank_frame("Connection Lost")

        return frame

    def _get_blank_frame(self, text):
        import numpy as np

        blank = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(
            blank, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
        )
        return blank

    def is_connected(self):
        return self.connected

    def release(self):
        if self.cap:
            self.cap.release()
