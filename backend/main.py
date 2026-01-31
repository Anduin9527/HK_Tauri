import cv2
import asyncio
import uvicorn
from fastapi import FastAPI, Response, UploadFile, File
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

from camera import Camera
from detector import DefectDetector

# Global State
camera = None
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
    global camera, detector, running
    print("Initialize Camera and Detector...")
    camera = Camera()
    detector = DefectDetector()
    running = True
    yield
    # Shutdown
    print("Shutting down...")
    running = False
    if camera:
        camera.release()


app.router.lifespan_context = lifespan


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


def generate_frames():
    global camera, detector
    while running:
        if not camera or not detector:
            time.sleep(0.1)
            continue

        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.1)
            continue

        # Inference
        results, annotated_frame = detector.predict(frame)

        # Encode for MJPEG
        ret, buffer = cv2.imencode(".jpg", annotated_frame)
        frame_bytes = buffer.tobytes()

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/status")
async def get_status():
    return {
        "camera_connected": camera.is_connected() if camera else False,
        "model_loaded": detector.is_loaded() if detector else False,
        "device": detector.device if detector else "unknown",
    }


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
