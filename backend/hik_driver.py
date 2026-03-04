import cv2
import time
import threading
import numpy as np
import sys
import os
import platform
from ctypes import *
import struct

def _is_truthy_env(name: str, default: str = "1") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() not in ("0", "false", "no", "off", "")

REQUIRE_HIK_SDK = _is_truthy_env("HIK_REQUIRE_SDK", "1")

def _add_windows_dll_dir(path: str) -> bool:
    try:
        if not path or not os.path.isdir(path):
            return False
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(path)
        env_path = os.environ.get("PATH", "")
        if path.lower() not in env_path.lower():
            os.environ["PATH"] = f"{path};{env_path}"
        return True
    except Exception:
        return False

def _configure_mvs_dll_search_paths():
    if platform.system() != "Windows":
        return

    is_64 = struct.calcsize("P") * 8 == 64
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")

    candidates = []

    if is_64:
        candidates.extend(
            [
                os.path.join(pf86, "Common Files", "MVS", "Runtime", "Win64_x64"),
                os.path.join(pf, "Common Files", "MVS", "Runtime", "Win64_x64"),
            ]
        )
    else:
        candidates.extend(
            [
                os.path.join(pf86, "Common Files", "MVS", "Runtime", "Win32_i86"),
                os.path.join(pf, "Common Files", "MVS", "Runtime", "Win32_i86"),
            ]
        )

    mv_env = os.getenv("MVCAM_COMMON_RUNENV")
    if mv_env:
        candidates.extend(
            [
                os.path.join(mv_env, "Bin"),
                os.path.join(mv_env, "Bin", "Win64_x64"),
                os.path.join(mv_env, "Bin", "Win32_i86"),
                os.path.join(mv_env, "Libraries"),
            ]
        )

    for p in candidates:
        _add_windows_dll_dir(p)

# SDK Import Logic
SDK_AVAILABLE = False
try:
    # 1. Try local MvImport (if copied to project)
    sys.path.append(os.path.join(os.getcwd(), "MvImport"))
    from MvImport.MvCameraControl_class import *
    from MvImport.PixelType_header import *
    from MvImport.CameraParams_header import *
    from MvImport.MvErrorDefine_const import *
    SDK_AVAILABLE = True
except Exception:
    try:
        # 2. Try Standard Hikvision Install Path
        if platform.system() == 'Windows':
            _configure_mvs_dll_search_paths()
            mv_env = os.getenv('MVCAM_COMMON_RUNENV')
            if mv_env:
                sdk_path = os.path.join(mv_env, "Samples", "Python", "MvImport")
                sys.path.append(sdk_path)
                from MvCameraControl_class import *
                from PixelType_header import *
                from CameraParams_header import *
                from MvErrorDefine_const import *
                SDK_AVAILABLE = True
    except Exception:
        pass

if not SDK_AVAILABLE:
    print("[HikDriver] MvImport not found/loadable. Running in MOCK mode.")

def get_hik_sdk_status():
    mv_env = os.getenv("MVCAM_COMMON_RUNENV")
    if SDK_AVAILABLE:
        return {
            "sdk_available": True,
            "sdk_required": REQUIRE_HIK_SDK,
            "sdk_hint": "Hikvision MVS SDK detected.",
        }
    hint = "未检测到海康 MVS SDK（MvImport）。请先安装 MVS SDK（并确保环境变量 MVCAM_COMMON_RUNENV 已配置），然后重启后端。"
    if mv_env:
        hint = f"检测到 MVCAM_COMMON_RUNENV={mv_env}，但 Python 未能导入 MvImport。请确认 MVS SDK 安装完整、版本匹配（Python/64位），并重启。"
    return {
        "sdk_available": False,
        "sdk_required": REQUIRE_HIK_SDK,
        "sdk_hint": hint,
    }

def decode_bytes(b_arr):
    """Helper to safely decode bytes from SDK structures."""
    try:
        # Filter null bytes
        return bytes(b_arr).split(b'\0', 1)[0].decode('utf-8')
    except:
        return "DecodeError"

def get_available_cameras():
    """
    Enumerates all available cameras and returns a list of dictionaries.
    """
    camera_list = []
    
    if not SDK_AVAILABLE:
        if REQUIRE_HIK_SDK:
            return []
        camera_list.append(
            {
                "index": 0,
                "name": "Mock Camera 1",
                "model": "MOCK-001",
                "serial": "SN00001",
                "type": "MOCK",
            }
        )
        return camera_list
    
    try:
        MvCamera.MV_CC_Initialize() # Ensure SDK is init
    except:
        pass

    deviceList = MV_CC_DEVICE_INFO_LIST()
    tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
    
    # EnumDevices
    ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
    if ret != 0:
        print(f"[HikDriver] EnumDevices fail! ret[0x{ret:x}]")
        return []

    if deviceList.nDeviceNum == 0:
        print("[HikDriver] No devices found.")
        return []

    for i in range(deviceList.nDeviceNum):
        mvcc_dev_info = cast(deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
        
        dev_info = {
            "index": i,
            "name": f"Camera {i}",
            "model": "Unknown",
            "serial": "Unknown",
            "type": "Unknown"
        }
        
        if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
            dev_info["type"] = "GIGE"
            str_model = decode_bytes(mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName)
            str_serial = decode_bytes(mvcc_dev_info.SpecialInfo.stGigEInfo.chSerialNumber)
            user_name = decode_bytes(mvcc_dev_info.SpecialInfo.stGigEInfo.chUserDefinedName)
            
            dev_info["model"] = str_model
            dev_info["serial"] = str_serial
            if user_name:
                dev_info["name"] = user_name
            else:
                dev_info["name"] = f"{str_model} ({str_serial})"
                
        elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
            dev_info["type"] = "USB"
            str_model = decode_bytes(mvcc_dev_info.SpecialInfo.stUsb3VInfo.chModelName)
            str_serial = decode_bytes(mvcc_dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber)
            user_name = decode_bytes(mvcc_dev_info.SpecialInfo.stUsb3VInfo.chUserDefinedName)

            dev_info["model"] = str_model
            dev_info["serial"] = str_serial
            if user_name:
                dev_info["name"] = user_name
            else:
                dev_info["name"] = f"{str_model} ({str_serial})"
        
        camera_list.append(dev_info)
        
    return camera_list


class HikCameraDriver:
    def __init__(self, index=0):
        self.index = index
        self.cam = None
        self.connected = False
        self.grabbing = False
        self._lock = threading.Lock()
        self.exposure_time_us = 50000.0
        self.gain_db = 0.0
        self.last_error_ret = None
        self.last_error_msg = None
        
        # Frame storage
        self.latest_frame = None
        self.latest_frame_raw = None
        self.frame_seq = 0
        self.frame_update_time = 0
        self._last_frame_pc = 0.0
        self.camera_fps = 0.0
        
        # Threading
        self.thread = None
        self.exit_event = threading.Event()

        # Buffer stuff
        self.convert_buf = None
        self.convert_buf_size = 0

        if SDK_AVAILABLE:
            self.cam = MvCamera()

    def _to_hex_str(self, num):
        if num < 0:
            num = num + 2**32
        return hex(num)

    def connect(self):
        """Connects to the camera and starts the grabbing thread."""
        with self._lock:
            self.last_error_ret = None
            self.last_error_msg = None
            if not SDK_AVAILABLE:
                if REQUIRE_HIK_SDK:
                    self.connected = False
                    self.grabbing = False
                    self.last_error_msg = "Hikvision MVS SDK not available"
                    print(f"[HikDriver-{self.index}] Connect failed: Hikvision MVS SDK not available")
                    return False
                self.connected = True
                self.grabbing = True
                print(f"[HikDriver-{self.index}] Connected (MOCK)")
                return True

            # Enumerate devices to get the pointer again
            deviceList = MV_CC_DEVICE_INFO_LIST()
            tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
            
            ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
            if ret != 0:
                self.last_error_ret = ret
                self.last_error_msg = "EnumDevices failed"
                print(f"[HikDriver] EnumDevices fail! ret[0x{ret:x}]")
                return False

            if deviceList.nDeviceNum == 0:
                self.last_error_msg = "No device found"
                print(f"[HikDriver] No device found")
                return False

            if self.index >= deviceList.nDeviceNum:
                self.last_error_msg = "Index out of range"
                print(f"[HikDriver] Index {self.index} out of range (Found {deviceList.nDeviceNum})")
                return False

            stDeviceList = cast(deviceList.pDeviceInfo[self.index], POINTER(MV_CC_DEVICE_INFO)).contents

            # Create handle
            ret = self.cam.MV_CC_CreateHandle(stDeviceList)
            if ret != 0:
                self.last_error_ret = ret
                self.last_error_msg = "CreateHandle failed"
                print(f"[HikDriver] Create Handle fail! ret[0x{ret:x}]")
                return False

            # Open device
            ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                self.last_error_ret = ret
                self.last_error_msg = "OpenDevice failed"
                print(f"[HikDriver] Open device fail! ret[0x{ret:x}]")
                if ret == 0x80000203: # MV_E_ACCESS_DENIED
                     print("[HikDriver] Error: Access Denied (Device is occupied)")
                self.cam.MV_CC_DestroyHandle()
                return False

            # Optimizations (Packet Size for GigE)
            if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
                nPacketSize = self.cam.MV_CC_GetOptimalPacketSize()
                if int(nPacketSize) > 0:
                    ret = self.cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)

            # Turn off Trigger Mode
            ret = self.cam.MV_CC_SetEnumValueByString("TriggerMode", "Off")
            
            # Start Grabbing
            ret = self.cam.MV_CC_StartGrabbing()
            if ret != 0:
                self.last_error_ret = ret
                self.last_error_msg = "StartGrabbing failed"
                print(f"[HikDriver] Start grabbing fail! ret[0x{ret:x}]")
                self.cam.MV_CC_CloseDevice()
                self.cam.MV_CC_DestroyHandle()
                return False

            self.connected = True
            self.grabbing = True
            self.exit_event.clear()
            
            # Start Background Thread
            self.thread = threading.Thread(target=self._grab_thread, daemon=True)
            self.thread.start()
            
            print(f"[HikDriver-{self.index}] Connected & Started Successfully")
            return True

    def set_exposure_time_us(self, exposure_time_us: float):
        with self._lock:
            self.exposure_time_us = float(exposure_time_us)
            if not SDK_AVAILABLE:
                if REQUIRE_HIK_SDK:
                    return False, "Hikvision MVS SDK not available"
                print(f"[HikDriver-{self.index}] Set ExposureTime={self.exposure_time_us}us (MOCK)")
                return True, "MOCK"
            if not self.connected or not self.cam:
                return False, "Camera not connected"

            ret = self.cam.MV_CC_SetEnumValue("ExposureAuto", 0)
            if ret != 0:
                return False, f"Disable ExposureAuto failed: {self._to_hex_str(ret)}"

            time.sleep(0.05)
            ret = self.cam.MV_CC_SetFloatValue("ExposureTime", float(self.exposure_time_us))
            if ret != 0:
                return False, f"Set ExposureTime failed: {self._to_hex_str(ret)}"

            return True, "OK"

    def set_gain_db(self, gain_db: float):
        with self._lock:
            self.gain_db = float(gain_db)
            if not SDK_AVAILABLE:
                if REQUIRE_HIK_SDK:
                    return False, "Hikvision MVS SDK not available"
                print(f"[HikDriver-{self.index}] Set Gain={self.gain_db}dB (MOCK)")
                return True, "MOCK"
            if not self.connected or not self.cam:
                return False, "Camera not connected"

            ret = self.cam.MV_CC_SetEnumValue("GainAuto", 0)
            if ret != 0:
                return False, f"Disable GainAuto failed: {self._to_hex_str(ret)}"

            time.sleep(0.05)
            ret = self.cam.MV_CC_SetFloatValue("Gain", float(self.gain_db))
            if ret != 0:
                return False, f"Set Gain failed: {self._to_hex_str(ret)}"

            return True, "OK"

    def apply_params(self, exposure_time_us: float | None = None, gain_db: float | None = None):
        ok = True
        msgs = []
        if exposure_time_us is not None:
            s, m = self.set_exposure_time_us(exposure_time_us)
            ok = ok and s
            msgs.append(f"Exposure={m}")
        if gain_db is not None:
            s, m = self.set_gain_db(gain_db)
            ok = ok and s
            msgs.append(f"Gain={m}")
        return ok, ", ".join(msgs) if msgs else "No-op"

    def _grab_thread(self):
        """Background thread to continuously grab frames using GetImageBuffer (Zero Copy)."""
        stOutFrame = MV_FRAME_OUT()
        memset(byref(stOutFrame), 0, sizeof(stOutFrame))
        
        while not self.exit_event.is_set():
            if not self.connected:
                time.sleep(0.1)
                continue

            # Get Frame (Pointer)
            ret = self.cam.MV_CC_GetImageBuffer(stOutFrame, 1000)
            
            if ret == 0:
                # Process
                self._process_frame(stOutFrame)
                # Free Buffer
                self.cam.MV_CC_FreeImageBuffer(stOutFrame)
            else:
                # Timeout is normal if no trigger, but here we are in continuous mode
                # print(f"[HikDriver-{self.index}] GetImageBuffer failed: {ret:x}")
                pass
                
    def _process_frame(self, stOutFrame):
        """Convert raw SDK frame to BGR numpy array using ConvertPixelTypeEx."""
        
        nWidth = stOutFrame.stFrameInfo.nWidth
        nHeight = stOutFrame.stFrameInfo.nHeight
        enPixelType = stOutFrame.stFrameInfo.enPixelType
        
        # print(f"[HikDriver-{self.index}] Frame: {nWidth}x{nHeight} Type: {enPixelType:x}")
        
        # 1. Direct BGR8 (Rare but possible)
        if enPixelType == PixelType_Gvsp_BGR8_Packed:
            # Copy memory to numpy
            size = nWidth * nHeight * 3
            if not self.convert_buf or self.convert_buf_size < size:
                self.convert_buf = (c_ubyte * size)()
                self.convert_buf_size = size
            
            memmove(self.convert_buf, stOutFrame.pBufAddr, size)
            image = np.ctypeslib.as_array(self.convert_buf, shape=(nHeight, nWidth, 3))
            self._update_latest_frame(image.copy())
            return
        
        # 2. Mono8 (Grayscale) - Convert to BGR for OpenCV
        if enPixelType == PixelType_Gvsp_Mono8:
            size = nWidth * nHeight
            if not self.convert_buf or self.convert_buf_size < size:
                self.convert_buf = (c_ubyte * size)()
                self.convert_buf_size = size
            
            # Copy raw Mono8 data
            memmove(self.convert_buf, stOutFrame.pBufAddr, size)
            
            try:
                # Use frombuffer + reshape for safety
                gray_image = np.frombuffer(self.convert_buf, dtype=np.uint8, count=size).reshape((nHeight, nWidth))
                self._update_latest_frame(gray_image.copy())
            except Exception as e:
                print(f"[HikDriver-{self.index}] Frame conversion failed: {e} (W:{nWidth} H:{nHeight})")
            return

        # 3. Convert other formats to BGR8 using SDK
        nRGBSize = nWidth * nHeight * 3
        
        # Prepare output buffer
        if not self.convert_buf or self.convert_buf_size < nRGBSize:
             self.convert_buf = (c_ubyte * nRGBSize)()
             self.convert_buf_size = nRGBSize

        stConvertParam = MV_CC_PIXEL_CONVERT_PARAM_EX()
        memset(byref(stConvertParam), 0, sizeof(stConvertParam))
        
        stConvertParam.nWidth = nWidth
        stConvertParam.nHeight = nHeight
        stConvertParam.pSrcData = stOutFrame.pBufAddr
        stConvertParam.nSrcDataLen = stOutFrame.stFrameInfo.nFrameLen
        stConvertParam.enSrcPixelType = enPixelType
        stConvertParam.enDstPixelType = PixelType_Gvsp_BGR8_Packed
        stConvertParam.pDstBuffer = self.convert_buf
        stConvertParam.nDstBufferSize = nRGBSize
        
        ret = self.cam.MV_CC_ConvertPixelTypeEx(stConvertParam)
        if ret == 0:
            # Success
            image = np.ctypeslib.as_array(self.convert_buf, shape=(nHeight, nWidth, 3))
            self._update_latest_frame(image.copy())
        else:
            print(f"[HikDriver-{self.index}] Convert Pixel Fail! ret={ret:x}")

    def _update_latest_frame(self, frame):
        with self._lock:
            # Store raw high-res frame for detection/saving
            self.latest_frame_raw = frame
            
            # Create resized preview frame for streaming (Max width 1920)
            if frame.shape[1] > 1920:
                scale = 1920 / frame.shape[1]
                new_height = int(frame.shape[0] * scale)
                self.latest_frame = cv2.resize(frame, (1920, new_height))
            else:
                self.latest_frame = frame
                
            self.frame_update_time = time.time()
            self.frame_seq += 1
            now_pc = time.perf_counter()
            if self._last_frame_pc:
                dt = now_pc - self._last_frame_pc
                if dt > 1e-6:
                    inst = 1.0 / dt
                    self.camera_fps = inst if self.camera_fps <= 0 else (self.camera_fps * 0.8 + inst * 0.2)
            self._last_frame_pc = now_pc

    def get_frame(self, raw=False):
        """Returns the latest frame. If raw=True, returns full resolution."""
        if not SDK_AVAILABLE:
            if REQUIRE_HIK_SDK:
                return None
            return self._get_mock_frame()

        with self._lock:
            if raw and hasattr(self, 'latest_frame_raw') and self.latest_frame_raw is not None:
                return self.latest_frame_raw.copy()
            
            if self.latest_frame is not None:
                return self.latest_frame.copy() 
            
        return None 

    def get_frame_meta(self, raw=False):
        if not SDK_AVAILABLE:
            if REQUIRE_HIK_SDK:
                return None, None, None, 0.0
            return self._get_mock_frame(), None, None, 0.0

        with self._lock:
            frame = self.latest_frame_raw if raw else self.latest_frame
            if frame is None:
                return None, None, None, float(self.camera_fps)
            return frame.copy(), int(self.frame_seq), float(self.frame_update_time), float(self.camera_fps)

    def _get_mock_frame(self, text=None):
        h, w = 480, 640
        canvas = np.zeros((h, w, 3), np.uint8)
        t = time.time()
        
        # Draw some pattern
        cv2.putText(canvas, f"MOCK CAM {self.index}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.circle(canvas, (int(w/2 + np.sin(t)*100), int(h/2)), 20, (0, 0, 255), -1)
        return canvas

    def release(self):
        """Stops grabbing and releases resources."""
        self.exit_event.set()
        try:
            if SDK_AVAILABLE and self.cam:
                with self._lock:
                    if self.grabbing:
                        try:
                            self.cam.MV_CC_StopGrabbing()
                        except:
                            pass
                        self.grabbing = False
                    if self.connected:
                        self.connected = False
        except:
            pass

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)

        with self._lock:
            if SDK_AVAILABLE and self.cam:
                try:
                    self.cam.MV_CC_CloseDevice()
                except:
                    pass
                try:
                    self.cam.MV_CC_DestroyHandle()
                except:
                    pass
        
        print(f"[HikDriver-{self.index}] Released")
