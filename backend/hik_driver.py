import cv2
import time
import threading
import numpy as np
import sys
import os
from ctypes import *

# Try to import MvImport (Hikvision SDK)
# Standard location assumption: ./MvImport
try:
    sys.path.append(os.path.join(os.getcwd(), "MvImport"))
    from MvImport.MvCameraControl_class import *  # type: ignore

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("[HikDriver] MvImport not found. Running in MOCK mode.")


class HikCameraDriver:
    def __init__(self, index=0):
        self.index = index
        self.cam = None
        self.connected = False
        self._lock = threading.Lock()

        # Buffer for SDK
        self.data_buf = None
        self.n_payload_size = 0

        if SDK_AVAILABLE:
            self.cam = MvCamera()

    def connect(self):
        """Attempts to connect to the camera at the specified index"""
        with self._lock:
            if not SDK_AVAILABLE:
                self.connected = True
                print(f"[HikDriver-{self.index}] Connected (MOCK)")
                return True

            # Enumerate devices
            deviceList = MV_CC_DEVICE_INFO_LIST()
            tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE

            ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
            if ret != 0:
                print(f"[HikDriver] EnumDevices fail! ret[0x{ret:x}]")
                return False

            if deviceList.nDeviceNum == 0:
                print(f"[HikDriver] No device found")
                return False

            if self.index >= deviceList.nDeviceNum:
                print(
                    f"[HikDriver] Index {self.index} out of range (Found {deviceList.nDeviceNum})"
                )
                return False

            stDeviceList = cast(
                deviceList.pDeviceInfo[self.index], POINTER(MV_CC_DEVICE_INFO)
            ).contents

            # Create handle
            ret = self.cam.MV_CC_CreateHandle(stDeviceList)
            if ret != 0:
                print(f"[HikDriver] Create Handle fail! ret[0x{ret:x}]")
                return False

            # Open device
            ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                print(f"[HikDriver] Open device fail! ret[0x{ret:x}]")
                return False

            # Get payload size
            stParam = MVCC_INTVALUE()
            memset(byref(stParam), 0, sizeof(MVCC_INTVALUE))
            ret = self.cam.MV_CC_GetIntValue("PayloadSize", stParam)
            if ret != 0:
                print(f"[HikDriver] Get PayloadSize fail! ret[0x{ret:x}]")
                return False

            self.n_payload_size = stParam.nCurValue
            self.data_buf = (c_ubyte * self.n_payload_size)()

            # Start grabbing
            ret = self.cam.MV_CC_StartGrabbing()
            if ret != 0:
                print(f"[HikDriver] Start grabbing fail! ret[0x{ret:x}]")
                return False

            self.connected = True
            print(f"[HikDriver-{self.index}] Connected Successfully")
            return True

    def get_frame(self):
        """Returns a numpy array (BGR) or None"""
        if not self.connected:
            # Auto-reconnect logic could go here
            return self._get_mock_frame("Not Connected")

        if not SDK_AVAILABLE:
            return self._get_mock_frame()

        with self._lock:
            stFrameInfo = MV_FRAME_OUT_INFO_EX()
            memset(byref(stFrameInfo), 0, sizeof(MV_FRAME_OUT_INFO_EX))

            # Timeout 1000ms
            ret = self.cam.MV_CC_GetOneFrameTimeout(
                self.data_buf, self.n_payload_size, stFrameInfo, 1000
            )
            if ret == 0:
                # Successful grab
                # Convert to numpy
                # Note: Currently handling raw mono/color might need pixel conversion
                # We assume basic pixel conversion for display

                # Check pixel format
                # For simplicity, we just assume we need to convert to BGR always if it's not
                # In a real impl, we uses MV_CC_ConvertPixelType logic

                # However, Python SDK usage for conversion is tricky without full struct
                # We will try a simpler path: If generic implementation, we use raw data
                # But typically we need nparray

                # IMPORTANT: Minimal implementation for now is to just return a valid shape
                # To actually visualize, we need ctypes to numpy copy

                # Create a buffer for BGR
                # Because converting in Python SDK is verbose, we recommend users configure camera to output BGR/RGB if possible
                # OR use the ConvertPixelType API.

                # Let's try basic buffer to numpy wrapper
                img_buff = (c_ubyte * stFrameInfo.nContentSize).from_address(
                    addressof(self.data_buf)
                )
                img_data = np.frombuffer(img_buff, dtype=np.uint8)

                # Reshape if direct raw
                # Warning: This depends heavily on camera setting (Mono8, Bayer, RGB8)
                # For robust industrial use, we should use MV_CC_ConvertPixelType inside here.
                # Due to complexity of implementing full conversion in this snippet without header files,
                # we assume the user sets camera to RGB or we might get raw BAYER/Mono

                # Heuristic:
                if stFrameInfo.enPixelType == PixelType_Gvsp_Mono8:
                    img = img_data.reshape((stFrameInfo.nHeight, stFrameInfo.nWidth))
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    return img
                elif stFrameInfo.enPixelType == PixelType_Gvsp_BGR8_Packed:
                    img = img_data.reshape((stFrameInfo.nHeight, stFrameInfo.nWidth, 3))
                    return img
                else:
                    # Fallback or Todo: Implement Conversion
                    pass

                return self._get_mock_frame(f"Raw fmt: {stFrameInfo.enPixelType}")
            else:
                # print(f"GetFrame fail: {ret}")
                return None

    def _get_mock_frame(self, text=None):
        h, w = 480, 640
        canvas = np.zeros((h, w, 3), np.uint8)

        # Industrial look
        t = time.time()

        # Crosshair
        cv2.line(canvas, (0, h // 2), (w, h // 2), (0, 50, 0), 1)
        cv2.line(canvas, (w // 2, 0), (w // 2, h), (0, 50, 0), 1)

        # Moving element
        offset = int((np.sin(t * 2) * 200))
        cv2.circle(canvas, (w // 2 + offset, h // 2), 30, (0, 255, 255), 2)

        # Info
        cv2.putText(
            canvas,
            f"HIK-ROBOT MOCK [{self.index}]",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        if text:
            cv2.putText(
                canvas, text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2
            )

        cv2.putText(
            canvas,
            time.strftime("%Y-%m-%d %H:%M:%S"),
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1,
        )
        return canvas

    def release(self):
        if SDK_AVAILABLE and self.cam and self.connected:
            self.cam.MV_CC_StopGrabbing()
            self.cam.MV_CC_CloseDevice()
            self.cam.MV_CC_DestroyHandle()
        self.connected = False
