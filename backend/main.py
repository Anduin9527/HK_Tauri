import cv2
import asyncio
import uvicorn
from fastapi import FastAPI, Response, UploadFile, File, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import socketio
from contextlib import asynccontextmanager
import threading
import time
import json
import numpy as np
import os
from pydantic import BaseModel
from typing import Dict, List

from hik_driver import HikCameraDriver
from detector import DefectDetector

# Global State
cameras: Dict[int, HikCameraDriver] = {}
detector = None
running = False

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure history directory exists
os.makedirs("history", exist_ok=True)
# Mount static files
app.mount("/history", StaticFiles(directory="history"), name="history")

# Wrap FastAPI with Socket.IO
final_app = socketio.ASGIApp(sio, app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global cameras, detector, running
    print("Initialize Detector...")
    detector = DefectDetector()

    print("Initialize 4 Hikvision Camera Slots...")
    # Initialize 4 slots using HikCameraDriver
    # Slot 0 attempts to access the first specific camera, etc.
    # Note: connect() inside HikCameraDriver handles connection logic

    for i in range(4):
        cameras[i] = HikCameraDriver(index=i)
        cameras[i].connect()

    running = True

    # Optional: Start background discovery or status check
    # threading.Thread(target=watchdog_cameras_bg, daemon=True).start()

    yield
    # Shutdown
    print("Shutting down...")
    running = False
    for cam in cameras.values():
        cam.release()


app.router.lifespan_context = lifespan


def discover_cameras_bg():
    time.sleep(2)  # Wait for app to start
    try:
        from find_cameras import scan_network, get_local_ip_and_subnet

        print("[Discovery] Starting background camera scan...")
        # Note: We need to adapt scan_network to return values instead of printing
        # For now, we skip auto-assign to avoid complexity,
        # but in production this would update cameras[i].set_source()
    except Exception as e:
        print(f"[Discovery] Error: {e}")


async def broadcast_log(
    title: str, message: str, level: str = "info", attachment: str = None
):
    """Emit log message to all connected clients and save to local file"""
    timestamp = time.strftime("%H:%M:%S")
    try:
        # 1. Print to console
        print(f"[LOG] {title}: {message}")

        # 2. Emit to Fronend via Socket.IO
        await sio.emit(
            "log_message",
            {
                "title": title,
                "message": message,
                "severity": level if level in ["info", "medium", "high"] else "info",
                "time": timestamp,
                "attachment": attachment,
            },
        )

        # 3. Save to local file
        os.makedirs("history", exist_ok=True)
        with open("history/events.log", "a", encoding="utf-8") as f:
            # Format: [TIME] [LEVEL] TITLE: MESSAGE | attachment=URL
            log_line = f"[{timestamp}] [{level.upper()}] {title}: {message}"
            if attachment:
                log_line += f" | attachment={attachment}"
            f.write(log_line + "\n")

    except Exception as e:
        print(f"Failed to log: {e}")


@app.post("/predict/image")
async def predict_image(file: UploadFile = File(...)):
    global detector
    if not detector:
        await broadcast_log("错误", "模型未加载", "high")
        return JSONResponse(status_code=500, content={"error": "Model not loaded"})

    try:
        contents = await file.read()

        # Save raw image
        filename_raw = f"raw_{int(time.time() * 1000)}.jpg"
        filepath_raw = os.path.join("history", filename_raw)
        with open(filepath_raw, "wb") as f:
            f.write(contents)

        raw_url = f"http://localhost:8000/history/{filename_raw}"
        await broadcast_log(
            "调试", f"接收到图片: {len(contents)} bytes", "info", attachment=raw_url
        )

        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            await broadcast_log("错误", "图片解码失败", "high")
            return JSONResponse(status_code=400, content={"error": "Invalid image"})

        # Inference
        start_time = time.time()
        results, annotated_frame = detector.predict(img)
        dt = time.time() - start_time

        det_count = len(results)
        msg_type = "high" if det_count > 0 else "info"

        # Save to history
        timestamp = int(time.time() * 1000)
        filename = f"detected_{timestamp}.jpg"
        filepath = os.path.join("history", filename)
        cv2.imwrite(filepath, annotated_frame)
        image_url = f"http://localhost:8000/history/{filename}"

        await broadcast_log(
            "推理完成",
            f"耗时 {dt * 1000:.1f}ms, 检测到 {det_count} 个目标",
            msg_type,
            attachment=image_url,
        )

        # Return URL
        return JSONResponse(
            content={
                "message": "Success",
                "detections": det_count,
                "image_url": image_url,
            }
        )

    except Exception as e:
        error_msg = f"处理异常: {str(e)}"
        print(error_msg)
        await broadcast_log("系统异常", error_msg, "high")
        return JSONResponse(status_code=500, content={"error": error_msg})


def generate_frames(camera_id: int):
    global cameras, detector, running

    # Basic rate limiting
    fps_limit = 30
    frame_duration = 1.0 / fps_limit

    while running:
        loop_start = time.time()

        cam = cameras.get(camera_id)
        if not cam or not detector:
            time.sleep(0.5)
            # Yield a keep-alive or error frame?
            continue

        frame = cam.get_frame()
        if frame is None:
            time.sleep(0.1)
            continue

        # Inference (Skip if too slow? For now we process every frame)
        # Note: 4x stream inference might be heavy.
        # Ideally we only infer on 1 stream or skip frames.
        # Here we do full processing.
        results, annotated_frame = detector.predict(frame)

        # Encode for MJPEG
        ret, buffer = cv2.imencode(".jpg", annotated_frame)
        frame_bytes = buffer.tobytes()

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

        # FPS Control
        elapsed = time.time() - loop_start
        if elapsed < frame_duration:
            time.sleep(frame_duration - elapsed)


@app.get("/video_feed/{camera_id}")
async def video_feed(camera_id: int = Path(..., ge=0, le=3)):
    return StreamingResponse(
        generate_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# Backward compatibility for existing frontend until we switch
@app.get("/video_feed")
async def video_feed_legacy():
    return await video_feed(0)


@app.get("/status")
async def get_status():
    status_data = {
        "model_loaded": detector.is_loaded() if detector else False,
        "device": detector.device if detector else "unknown",
        "cameras": [],
    }

    for i in range(4):
        cam = cameras.get(i)
        status_data["cameras"].append(
            {
                "id": i,
                "connected": cam.connected if cam else False,
                "index": cam.index if cam else None,
            }
        )
    return status_data

    return status_data


# --- New Endpoints for Logs and Settings ---


@app.get("/logs")
async def get_logs(lines: int = 50):
    try:
        log_file = "history/events.log"
        if not os.path.exists(log_file):
            return {"logs": []}

        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            # Return last N lines
            recent_lines = all_lines[-lines:]
            # Parse simple format if needed, or return raw strings
            # Format: [HH:MM:SS] [LEVEL] TITLE: MESSAGE
            parsed_logs = []
            for line in recent_lines:
                try:
                    parts = line.strip().split("] ", 2)
                    if len(parts) >= 3:
                        time_str = parts[0].strip("[")
                        level_str = parts[1].strip("[")
                        content = parts[2]
                        if ": " in content:
                            title, msg = content.split(": ", 1)
                        else:
                            title, msg = "System", content

                        parsed_logs.append(
                            {
                                "time": time_str,
                                "severity": level_str.lower(),
                                "title": title,
                                "message": msg,
                            }
                        )
                        # Try to parse attachment from log line
                        if " | attachment=" in msg:
                            clean_msg, att = msg.split(" | attachment=", 1)
                            parsed_logs[-1]["message"] = clean_msg
                            parsed_logs[-1]["attachment"] = att.strip()
                except:
                    continue

            return {"logs": list(reversed(parsed_logs))}  # Newest first
    except Exception as e:
        return {"error": str(e), "logs": []}


class SettingsModel(BaseModel):
    conf: float
    imgsz: int


@app.get("/config/settings")
async def get_settings():
    if detector:
        return {"conf": detector.conf, "imgsz": detector.imgsz}
    return {"conf": 0.25, "imgsz": 640}


@app.post("/config/settings")
async def update_settings(settings: SettingsModel):
    if detector:
        detector.update_settings(conf=settings.conf, imgsz=settings.imgsz)
        await broadcast_log(
            "配置",
            f"系统参数已更新: Conf={settings.conf}, Size={settings.imgsz}",
            "medium",
        )
        return {"status": "updated", "conf": detector.conf, "imgsz": detector.imgsz}
    return JSONResponse(status_code=500, content={"error": "Detector not initialized"})


if __name__ == "__main__":
    uvicorn.run("main:final_app", host="0.0.0.0", port=8000, reload=True)
