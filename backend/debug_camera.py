import cv2
import time
import sys
import os
import platform
import threading
import numpy as np
from ctypes import *

# SDK Import Logic
SDK_AVAILABLE = False
try:
    # 1. Try local MvImport
    sys.path.append(os.path.join(os.getcwd(), "MvImport"))
    from MvImport.MvCameraControl_class import *
    from MvImport.PixelType_header import *
    from MvImport.CameraParams_header import *
    from MvImport.MvErrorDefine_const import *
    SDK_AVAILABLE = True
except ImportError:
    try:
        # 2. Try Standard Hikvision Install Path
        if platform.system() == 'Windows':
            mv_env = os.getenv('MVCAM_COMMON_RUNENV')
            if mv_env:
                sdk_path = os.path.join(mv_env, "Samples", "Python", "MvImport")
                sys.path.append(sdk_path)
                from MvCameraControl_class import *
                from PixelType_header import *
                from CameraParams_header import *
                from MvErrorDefine_const import *
                SDK_AVAILABLE = True
    except ImportError:
        pass

if not SDK_AVAILABLE:
    print("[ERROR] Hikvision SDK (MvImport) not found! Cannot run test.")
    sys.exit(1)

def main():
    print("Initializing SDK...")
    MvCamera.MV_CC_Initialize()
    
    deviceList = MV_CC_DEVICE_INFO_LIST()
    tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
    
    ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
    if ret != 0:
        print(f"EnumDevices fail! ret[0x{ret:x}]")
        sys.exit(1)

    if deviceList.nDeviceNum == 0:
        print("No devices found.")
        sys.exit(1)

    print(f"Found {deviceList.nDeviceNum} devices.")
    
    # Select first device
    nConnectionNum = 0
    stDeviceList = cast(deviceList.pDeviceInfo[nConnectionNum], POINTER(MV_CC_DEVICE_INFO)).contents

    cam = MvCamera()
    
    ret = cam.MV_CC_CreateHandle(stDeviceList)
    if ret != 0:
        print(f"Create Handle fail! ret[0x{ret:x}]")
        sys.exit(1)

    ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
    if ret != 0:
        print(f"Open device fail! ret[0x{ret:x}]")
        sys.exit(1)
        
    # Get Packet Size (GigE)
    if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
        nPacketSize = cam.MV_CC_GetOptimalPacketSize()
        if int(nPacketSize) > 0:
            cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)

    # Set Trigger Mode Off
    cam.MV_CC_SetEnumValueByString("TriggerMode", "Off")
    
    # Set Bayer Interpolation Quality (Balance)
    # 0-Fast, 1-Balance, 2-Optimal
    # Only works for Bayer formats
    cam.MV_CC_SetBayerCvtQuality(1)

    # Start Grabbing
    ret = cam.MV_CC_StartGrabbing()
    if ret != 0:
        print(f"Start grabbing fail! ret[0x{ret:x}]")
        sys.exit(1)

    print("Stream started. Press 'q' to exit.")

    stOutFrame = MV_FRAME_OUT()
    memset(byref(stOutFrame), 0, sizeof(stOutFrame))
    
    # Allocate convert param and buffer once to save perf
    # But size might change, so we check inside loop
    convert_buf = None
    convert_buf_size = 0

    try:
        while True:
            # Use GetImageBuffer (New API, Zero Copy for Src)
            ret = cam.MV_CC_GetImageBuffer(stOutFrame, 1000)
            
            if ret == 0:
                # print(f"Frame: {stOutFrame.stFrameInfo.nWidth}x{stOutFrame.stFrameInfo.nHeight} Type: {stOutFrame.stFrameInfo.enPixelType:x}")
                
                nWidth = stOutFrame.stFrameInfo.nWidth
                nHeight = stOutFrame.stFrameInfo.nHeight
                enPixelType = stOutFrame.stFrameInfo.enPixelType
                
                image = None

                # 1. Check if already BGR8 (OpenCV default)
                if enPixelType == PixelType_Gvsp_BGR8_Packed:
                    # Direct copy
                    # We can create numpy array from the buffer address
                    # But ctypes pointers are tricky with numpy. 
                    # Safest is string/buffer copy.
                    
                    # Method A: ctypes memmove to new buffer then numpy
                    size = nWidth * nHeight * 3
                    if convert_buf_size < size:
                        convert_buf = (c_ubyte * size)()
                        convert_buf_size = size
                    memmove(convert_buf, stOutFrame.pBufAddr, size)
                    image = np.ctypeslib.as_array(convert_buf, shape=(nHeight, nWidth, 3))
                
                elif enPixelType == PixelType_Gvsp_Mono8:
                    # Mono8 -> BGR for display
                    print("DEBUG: Processing as Mono8")
                    size = nWidth * nHeight
                    if convert_buf_size < size:
                        convert_buf = (c_ubyte * size)()
                        convert_buf_size = size
                    memmove(convert_buf, stOutFrame.pBufAddr, size)
                    
                    # Construct numpy array carefully
                    try:
                        gray_image = np.frombuffer(convert_buf, dtype=np.uint8, count=size).reshape((nHeight, nWidth))
                        image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)
                    except Exception as e:
                        print(f"DEBUG: Numpy reshape failed: {e}")

                else:
                    # 3. Convert to BGR8
                    print(f"DEBUG: Converting from 0x{enPixelType:x} to BGR8")
                    # We use ConvertPixelTypeEx as per sample
                    
                    nRGBSize = nWidth * nHeight * 3
                    if convert_buf_size < nRGBSize:
                        convert_buf = (c_ubyte * nRGBSize)()
                        convert_buf_size = nRGBSize
                    
                    stConvertParam = MV_CC_PIXEL_CONVERT_PARAM_EX()
                    memset(byref(stConvertParam), 0, sizeof(stConvertParam))
                    
                    stConvertParam.nWidth = nWidth
                    stConvertParam.nHeight = nHeight
                    stConvertParam.pSrcData = stOutFrame.pBufAddr
                    stConvertParam.nSrcDataLen = stOutFrame.stFrameInfo.nFrameLen
                    stConvertParam.enSrcPixelType = enPixelType
                    stConvertParam.enDstPixelType = PixelType_Gvsp_BGR8_Packed # Convert directly to BGR for OpenCV
                    stConvertParam.pDstBuffer = convert_buf
                    stConvertParam.nDstBufferSize = nRGBSize
                    
                    ret_conv = cam.MV_CC_ConvertPixelTypeEx(stConvertParam)
                    if ret_conv == 0:
                        image = np.ctypeslib.as_array(convert_buf, shape=(nHeight, nWidth, 3))
                    else:
                        print(f"Convert fail: 0x{ret_conv:x}")

                # Free buffer immediately after copy/convert
                cam.MV_CC_FreeImageBuffer(stOutFrame)

                if image is not None:
                    # Resize for display if too big
                    display_img = image
                    if nWidth > 1024:
                        display_img = cv2.resize(image, (1024, int(1024*nHeight/nWidth)))
                    
                    cv2.imshow("Hikvision Test Stream", display_img)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # print(f"GetImageBuffer fail! ret[0x{ret:x}]")
                pass
                
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping...")
        cam.MV_CC_StopGrabbing()
        cam.MV_CC_CloseDevice()
        cam.MV_CC_DestroyHandle()
        MvCamera.MV_CC_Finalize()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
