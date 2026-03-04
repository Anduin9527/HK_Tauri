import cv2
import uvicorn
import asyncio
from fastapi import FastAPI, Response, UploadFile, File, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import socketio
from contextlib import asynccontextmanager
import threading
import time
import numpy as np
import os
import sys
import ctypes
from pydantic import BaseModel
from typing import Dict, List

from hik_driver import HikCameraDriver, get_available_cameras, get_hik_sdk_status
from detector import DefectDetector
from config_store import load_settings, save_settings, default_settings, _config_path as get_config_path


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _start_parent_watchdog() -> None:
    raw = os.environ.get("HK_TAURI_PARENT_PID") or ""
    raw = raw.strip()
    if not raw:
        return
    try:
        parent_pid = int(raw)
    except Exception:
        return

    def _watch():
        while True:
            if not _is_pid_alive(parent_pid):
                os._exit(0)
            time.sleep(1.0)

    t = threading.Thread(target=_watch, daemon=True)
    t.start()


_start_parent_watchdog()

# Global State
cameras: Dict[int, HikCameraDriver] = {}
camera_detections: Dict[int, List] = {0: [], 1: [], 2: [], 3: []} # Store latest detections per camera
detector = None
running = False
# Auto-inference control: True = detect every frame, False = only on trigger
auto_inference = False
is_manual_mode = True  # If True, disable auto-inference in stream

stream_state: Dict[int, Dict] = {}
stream_tasks: Dict[int, asyncio.Task] = {}
fps_broadcast_task: asyncio.Task | None = None

sdk_op_lock: asyncio.Lock | None = None
slot_op_locks: Dict[int, asyncio.Lock] = {}
device_op_locks: Dict[int, asyncio.Lock] = {}

model_reload_lock: asyncio.Lock | None = None
model_reloading = False

# Logging throttling
log_cooldown = 10.0 # seconds
last_log_time: Dict[int, float] = {} 

persisted_settings = default_settings()


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _get_app_data_dir() -> str:
    base_dir = os.environ.get("HK_TAURI_DATA_DIR") or os.environ.get("HK_TAURI_CONFIG_DIR")
    if base_dir:
        return base_dir

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, "HK_Tauri_Data")

    base_dir = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if base_dir:
        return os.path.join(base_dir, "HK_Tauri_Data")
    return os.path.join(os.getcwd(), "HK_Tauri_Data")


def _pick_writable_data_dir(preferred: str) -> str:
    try:
        os.makedirs(os.path.join(preferred, "history"), exist_ok=True)
        return preferred
    except Exception:
        base_dir = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        fallback = os.path.join(base_dir, "HK_Tauri_Data") if base_dir else os.path.join(os.getcwd(), "HK_Tauri_Data")
        os.makedirs(os.path.join(fallback, "history"), exist_ok=True)
        return fallback


APP_DATA_DIR = _pick_writable_data_dir(_get_app_data_dir())
HISTORY_DIR = os.path.join(APP_DATA_DIR, "history")
EVENTS_LOG_PATH = os.path.join(HISTORY_DIR, "events.log")

os.makedirs(HISTORY_DIR, exist_ok=True)
app.mount("/history", StaticFiles(directory=HISTORY_DIR), name="history")

# Wrap FastAPI with Socket.IO
final_app = socketio.ASGIApp(sio, app)

@app.get("/paths")
async def get_paths():
    return {
        "data_dir": APP_DATA_DIR,
        "history_dir": HISTORY_DIR,
        "events_log_path": EVENTS_LOG_PATH,
        "config_path": get_config_path(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global cameras, detector, running, log_cooldown, persisted_settings, is_manual_mode, auto_inference, stream_state, stream_tasks, fps_broadcast_task, sdk_op_lock, slot_op_locks, device_op_locks, model_reload_lock
    
    persisted_settings = load_settings()
    log_cooldown = float(persisted_settings.get("log_interval", log_cooldown))
    is_manual_mode = bool(persisted_settings.get("manual_mode", True))
    auto_inference = not is_manual_mode
    print(f"DATA_DIR={APP_DATA_DIR}")
    print(f"HISTORY_DIR={HISTORY_DIR}")
    print(f"CONFIG_PATH={get_config_path()}")

    # 1. Initialize Detector
    print("-" * 30)
    print("CORE SYSTEM STARTUP: Initializing AI Engine...")
    try:
        detector = DefectDetector()
        try:
            await asyncio.to_thread(
                detector.update_settings,
                conf=float(persisted_settings.get("conf", detector.conf)),
                imgsz=int(persisted_settings.get("imgsz", detector.imgsz)),
            )
        except Exception:
            pass

        try:
            mt = str(persisted_settings.get("model_type", "auto"))
            mn = str(persisted_settings.get("model_name", "yolo26s"))
            if mt == "auto":
                detector.reload_model("auto", mn)
            elif mt != detector.current_model_type:
                detector.reload_model(mt, mn)
        except Exception:
            pass

        if not detector.is_loaded():
             print("[ERROR] AI Engine Initialization Failed: No model loaded.")
             print("        Please ensure 'models/best.pt' (or .onnx/openvino) exists.")
        else:
             print(f"[SUCCESS] AI Engine Ready.")
             print(f"          - Model: {detector.model_path}")
             print(f"          - Type: {detector.current_model_type}")
             print(f"          - Device: {detector.device}")
             print(f"          - Settings: conf={detector.conf}, imgsz={detector.imgsz}")
    except Exception as e:
        print(f"[CRITICAL] AI Engine Exception: {e}")
        import traceback
        traceback.print_exc()

    # 2. Initialize Camera Slots
    print("-" * 30)
    print("CORE SYSTEM STARTUP: Initializing Camera Slots...")
    # Initialize 4 slots but DO NOT connect yet
    for i in range(4):
        cameras[i] = HikCameraDriver(index=i)
        # Note: We do not call cameras[i].connect() here anymore.
        # User must manually select camera via frontend.
    print(f"[SUCCESS] {len(cameras)} Camera Slots Prepared (Idle Mode).")
    print("-" * 30)
    
    running = True
    if sdk_op_lock is None:
        sdk_op_lock = asyncio.Lock()
    if model_reload_lock is None:
        model_reload_lock = asyncio.Lock()
    slot_op_locks = {i: asyncio.Lock() for i in range(4)}
    device_op_locks = {}
    stream_state = {
        i: {
            "cond": asyncio.Condition(),
            "seq": 0,
            "jpeg": {"grid": {"raw": None, "detect": None}, "full": {"raw": None, "detect": None}},
            "watchers": {"grid": {"raw": 0, "detect": 0}, "full": {"raw": 0, "detect": 0}},
            "stats": {
                "camera_fps": 0.0,
                "capture_fps": 0.0,
                "stream_fps": 0.0,
                "infer_fps": 0.0,
                "infer_ms": 0.0,
                "infer_updated_at": 0.0,
                "updated_at": 0.0,
            },
        }
        for i in range(4)
    }
    stream_tasks = {i: asyncio.create_task(_camera_stream_worker(i)) for i in range(4)}
    fps_broadcast_task = asyncio.create_task(_broadcast_fps_loop())

    yield
    # Shutdown
    print("Shutting down...")
    running = False
    for t in list(stream_tasks.values()):
        t.cancel()
    stream_tasks = {}
    if fps_broadcast_task:
        fps_broadcast_task.cancel()
        fps_broadcast_task = None
    for cam in cameras.values():
        cam.release()


app.router.lifespan_context = lifespan


async def broadcast_log(
    title: str, message: str, level: str = "info", attachment: str = None
):
    """Emit log message to all connected clients and save to local file"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
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
        os.makedirs(HISTORY_DIR, exist_ok=True)
        with open(EVENTS_LOG_PATH, "a", encoding="utf-8") as f:
            # Format: [TIME] [LEVEL] TITLE: MESSAGE | attachment=URL
            log_line = f"[{timestamp}] [{level.upper()}] {title}: {message}"
            if attachment:
                log_line += f" | attachment={attachment}"
            f.write(log_line + "\n")

    except Exception as e:
        print(f"Failed to log: {e}")


@app.post("/predict/image")
async def predict_image(file: UploadFile = File(...)):
    global detector, cameras
    
    # Restriction: Ensure no cameras are connected to avoid concurrency/resource conflicts
    active_cameras = [cam.index for cam in cameras.values() if cam.connected]
    if active_cameras:
        msg = "请先断开所有摄像头连接，再进行图片检测。"
        await broadcast_log("操作受限", msg, "high")
        return JSONResponse(status_code=400, content={"error": msg})

    if not detector:
        await broadcast_log("错误", "模型未加载", "high")
        return JSONResponse(status_code=500, content={"error": "Model not loaded"})

    try:
        contents = await file.read()

        # Save raw image
        filename_raw = f"raw_{int(time.time() * 1000)}.jpg"
        filepath_raw = os.path.join(HISTORY_DIR, filename_raw)
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
        # Use to_thread to prevent blocking event loop during heavy inference
        results, annotated_frame = await asyncio.to_thread(detector.predict, img)
        dt = time.time() - start_time

        det_count = len(results)
        msg_type = "high" if det_count > 0 else "info"
        if det_count > 0:
            pass

        # Save to history
        timestamp = int(time.time() * 1000)
        filename = f"detected_{timestamp}.jpg"
        filepath = os.path.join(HISTORY_DIR, filename)
        await asyncio.to_thread(cv2.imwrite, filepath, annotated_frame)
        image_url = f"http://localhost:8000/history/{filename}"

        await broadcast_log(
            "推理完成",
            f"耗时 {dt * 1000:.1f}ms, 目标数: {det_count} | Model={detector.model_name}/{detector.current_model_type} ({detector.device}) | conf={detector.conf}, imgsz={detector.imgsz}",
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


def draw_detections(frame, detections):
    """Draw detections on frame using OpenCV (with PIL for Chinese support)"""
    if not detections:
        return frame

    if frame is not None and hasattr(frame, "ndim") and frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame is not None and hasattr(frame, "shape") and len(frame.shape) == 3 and frame.shape[2] == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    
    img = frame
    
    # Label mapping
    label_map_cn = {"item": "缺陷", "defect": "缺陷"}
    label_map_en = {"item": "QueXian", "defect": "Defect"}

    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Convert to PIL
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        # Load Font (Windows: Microsoft YaHei)
        font = None
        try:
            font = ImageFont.truetype("msyh.ttc", 20)
        except IOError:
            try:
                font = ImageFont.truetype("simhei.ttf", 20)
            except IOError:
                font = ImageFont.load_default()

        for det in detections:
            xyxy = det.get("xyxy")
            if not xyxy: continue
            x1, y1, x2, y2 = map(int, xyxy[0])
            conf = det.get("conf", 0)
            raw_label = det.get("label", "Unknown")
            
            # Use Chinese label if font supports it (msyh/simhei), otherwise fallback
            label = label_map_cn.get(raw_label.lower(), raw_label)
            
            color = (0, 255, 0)
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            
            text = f"{label} {conf:.2f}"
            bbox = draw.textbbox((x1, y1 - 25), text, font=font)
            draw.rectangle(bbox, fill=color)
            draw.text((x1, y1 - 25), text, font=font, fill=(255, 255, 255))
            
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    except Exception as e:
        # Fallback to OpenCV
        for det in detections:
            xyxy = det.get("xyxy")
            if not xyxy: continue
            x1, y1, x2, y2 = map(int, xyxy[0])
            conf = det.get("conf", 0)
            raw_label = det.get("label", "Unknown")
            # Use Pinyin/English to avoid garbage chars
            label = label_map_en.get(raw_label.lower(), raw_label)
            
            color = (0, 255, 0)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            text = f"{label} {conf:.2f}"
            t_size = cv2.getTextSize(text, 0, fontScale=0.5, thickness=1)[0]
            c2 = x1 + t_size[0], y1 - t_size[1] - 3
            cv2.rectangle(img, (x1, y1), c2, color, -1, cv2.LINE_AA)  # filled
            cv2.putText(img, text, (x1, y1 - 2), 0, 0.5, [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)
        
    return img

def _resize_to_width(frame, target_width: int):
    if frame is None:
        return None
    h, w = frame.shape[:2]
    if w <= target_width:
        return frame
    scale = target_width / float(w)
    new_h = int(h * scale)
    return cv2.resize(frame, (target_width, new_h))


def _scale_detections_xyxy(detections, sx: float, sy: float):
    if not detections or (sx == 1.0 and sy == 1.0):
        return detections
    scaled = []
    for det in detections:
        xyxy = det.get("xyxy")
        if not xyxy:
            continue
        x1, y1, x2, y2 = xyxy[0]
        scaled_det = dict(det)
        scaled_det["xyxy"] = [[x1 * sx, y1 * sy, x2 * sx, y2 * sy]]
        bbox = det.get("bbox")
        if bbox and len(bbox) == 1 and len(bbox[0]) == 4:
            x, y, bw, bh = bbox[0]
            scaled_det["bbox"] = [[x * sx, y * sy, bw * sx, bh * sy]]
        scaled.append(scaled_det)
    return scaled


def _encode_jpeg(frame, quality: int):
    if frame is None:
        return None
    params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    ok, buf = cv2.imencode(".jpg", frame, params)
    if not ok:
        return None
    return buf.tobytes()


def _build_encoded_variants(full_frame, grid_frame, dets_full, dets_grid, quality_full: int, quality_grid: int):
    full_raw = _encode_jpeg(full_frame, quality_full)
    grid_raw = _encode_jpeg(grid_frame, quality_grid)

    if dets_full:
        full_detect = _encode_jpeg(draw_detections(full_frame.copy(), dets_full), quality_full)
    else:
        full_detect = full_raw

    if dets_grid:
        grid_detect = _encode_jpeg(draw_detections(grid_frame.copy(), dets_grid), quality_grid)
    else:
        grid_detect = grid_raw

    return {
        ("full", "raw"): full_raw,
        ("full", "detect"): full_detect,
        ("grid", "raw"): grid_raw,
        ("grid", "detect"): grid_detect,
    }


async def _camera_stream_worker(camera_id: int):
    global cameras, detector, running, auto_inference, camera_detections, stream_state, last_log_time, model_reloading

    fps_limit = 30
    frame_duration = 1.0 / fps_limit
    inference_interval = 0.1

    grid_width = 960
    full_quality = 80
    grid_quality = 75

    last_inference_time = 0.0
    infer_ms_ema = 0.0
    infer_fps_ema = 0.0
    last_stream_tick = 0.0
    last_infer_tick = 0.0
    stream_fps_ema = 0.0
    last_frame_seq = None

    while running:
        loop_start_pc = time.perf_counter()

        try:
            cam = cameras.get(camera_id)
            if not cam or not cam.connected:
                await asyncio.sleep(0.2)
                continue

            st = stream_state.get(camera_id)
            if not st:
                await asyncio.sleep(0.2)
                continue

            if not isinstance(st.get("watchers"), dict):
                st["watchers"] = {"grid": {"raw": 0, "detect": 0}, "full": {"raw": 0, "detect": 0}}
            watchers = st["watchers"]
            needs_grid = bool((watchers.get("grid") or {}).get("raw", 0) > 0 or (watchers.get("grid") or {}).get("detect", 0) > 0)
            needs_full = bool((watchers.get("full") or {}).get("raw", 0) > 0 or (watchers.get("full") or {}).get("detect", 0) > 0)
            wants_any = needs_grid or needs_full
            wants_detect = bool((watchers.get("grid") or {}).get("detect", 0) > 0 or (watchers.get("full") or {}).get("detect", 0) > 0)

            if not wants_any:
                camera_detections[camera_id] = []
                infer_ms_ema = 0.0
                infer_fps_ema = 0.0
                await asyncio.sleep(0.2)
                continue

            full_frame, frame_seq, _, cam_fps = cam.get_frame_meta(raw=False)
            if full_frame is None:
                await asyncio.sleep(0.01)
                continue
            if frame_seq is not None and frame_seq == last_frame_seq:
                await asyncio.sleep(0.005)
                continue
            last_frame_seq = frame_seq

            now_pc = time.perf_counter()
            now_wall = time.time()

            grid_frame = None
            if needs_grid or wants_detect:
                grid_frame = await asyncio.to_thread(_resize_to_width, full_frame, grid_width)
                if grid_frame is None:
                    await asyncio.sleep(0.01)
                    continue

            should_infer = False
            if (not model_reloading) and detector and auto_inference and wants_detect and (now_pc - last_inference_time >= inference_interval) and (grid_frame is not None):
                should_infer = True
                last_inference_time = now_pc

            if should_infer:
                t0 = time.perf_counter()
                results, _ = await asyncio.to_thread(detector.predict, grid_frame, False)
                infer_ms = (time.perf_counter() - t0) * 1000.0
                infer_ms_ema = infer_ms if infer_ms_ema <= 0 else (infer_ms_ema * 0.8 + infer_ms * 0.2)
                camera_detections[camera_id] = results
                infer_end = time.perf_counter()
                if last_infer_tick:
                    inst = 1.0 / max(1e-6, (infer_end - last_infer_tick))
                    infer_fps_ema = inst if infer_fps_ema <= 0 else (infer_fps_ema * 0.8 + inst * 0.2)
                last_infer_tick = infer_end

                if len(results) > 0:
                    last_log = last_log_time.get(camera_id, 0)
                    if now_wall - last_log > log_cooldown:
                        timestamp = int(now_wall * 1000)
                        filename = f"auto_detect_slot{camera_id}_{timestamp}.jpg"
                        filepath = os.path.join(HISTORY_DIR, filename)
                        annotated = await asyncio.to_thread(draw_detections, grid_frame.copy(), results)
                        await asyncio.to_thread(cv2.imwrite, filepath, annotated)
                        image_url = f"http://localhost:8000/history/{filename}"
                        await broadcast_log(
                            f"实时告警 (Cam {camera_id})",
                            f"发现 {len(results)} 个异常目标 | Model={detector.model_name}/{detector.current_model_type} ({detector.device}) | conf={detector.conf}, imgsz={detector.imgsz}",
                            "medium",
                            attachment=image_url,
                        )
                        last_log_time[camera_id] = now_wall
            else:
                camera_detections[camera_id] = []
                infer_ms_ema = 0.0
                infer_fps_ema = 0.0

            dets_grid = camera_detections.get(camera_id, []) if (grid_frame is not None) else []
            dets_full = []
            if needs_full and wants_detect and dets_grid and grid_frame is not None:
                sx = full_frame.shape[1] / float(grid_frame.shape[1])
                sy = full_frame.shape[0] / float(grid_frame.shape[0])
                dets_full = _scale_detections_xyxy(dets_grid, sx, sy)

            encoded = {}
            if needs_grid and grid_frame is not None:
                grid_raw = await asyncio.to_thread(_encode_jpeg, grid_frame, grid_quality)
                encoded[("grid", "raw")] = grid_raw
                if (watchers.get("grid") or {}).get("detect", 0) > 0:
                    if dets_grid:
                        grid_detect = await asyncio.to_thread(_encode_jpeg, draw_detections(grid_frame.copy(), dets_grid), grid_quality)
                        encoded[("grid", "detect")] = grid_detect
                    else:
                        encoded[("grid", "detect")] = grid_raw

            if needs_full:
                full_raw = await asyncio.to_thread(_encode_jpeg, full_frame, full_quality)
                encoded[("full", "raw")] = full_raw
                if (watchers.get("full") or {}).get("detect", 0) > 0:
                    if dets_full:
                        full_detect = await asyncio.to_thread(_encode_jpeg, draw_detections(full_frame.copy(), dets_full), full_quality)
                        encoded[("full", "detect")] = full_detect
                    else:
                        encoded[("full", "detect")] = full_raw

            now_pc2 = time.perf_counter()
            inst_stream = 0.0 if not last_stream_tick else 1.0 / max(1e-6, (now_pc2 - last_stream_tick))
            stream_fps_ema = inst_stream if stream_fps_ema <= 0 else (stream_fps_ema * 0.8 + inst_stream * 0.2)
            last_stream_tick = now_pc2

            async with st["cond"]:
                st["seq"] += 1
                st["jpeg"]["grid"]["raw"] = encoded.get(("grid", "raw")) if needs_grid else None
                st["jpeg"]["grid"]["detect"] = encoded.get(("grid", "detect")) if (watchers.get("grid") or {}).get("detect", 0) > 0 else None
                st["jpeg"]["full"]["raw"] = encoded.get(("full", "raw")) if needs_full else None
                st["jpeg"]["full"]["detect"] = encoded.get(("full", "detect")) if (watchers.get("full") or {}).get("detect", 0) > 0 else None
                st["stats"]["camera_fps"] = float(cam_fps or 0.0)
                st["stats"]["capture_fps"] = float(cam_fps or 0.0)
                st["stats"]["stream_fps"] = float(stream_fps_ema)
                st["stats"]["infer_fps"] = float(infer_fps_ema)
                st["stats"]["infer_ms"] = float(infer_ms_ema)
                st["stats"]["infer_updated_at"] = float(now_wall if should_infer else 0.0)
                st["stats"]["updated_at"] = float(now_wall)
                st["cond"].notify_all()
        except Exception as e:
            try:
                await broadcast_log("错误", f"StreamWorker[{camera_id}]异常: {e}", "high")
            except Exception:
                pass
            await asyncio.sleep(0.1)

        elapsed = time.perf_counter() - loop_start_pc
        if elapsed < frame_duration:
            await asyncio.sleep(frame_duration - elapsed)


async def _stream_generator(camera_id: int, profile: str, view_type: str):
    global running, stream_state
    if profile not in ("grid", "full"):
        profile = "grid"
    if view_type not in ("raw", "detect"):
        view_type = "detect"

    st = stream_state.get(camera_id)
    if not st:
        return
    if not isinstance(st.get("watchers"), dict):
        st["watchers"] = {"grid": {"raw": 0, "detect": 0}, "full": {"raw": 0, "detect": 0}}
    async with st["cond"]:
        prof = st["watchers"].get(profile)
        if not isinstance(prof, dict):
            prof = {"raw": 0, "detect": 0}
            st["watchers"][profile] = prof
        prof[view_type] = int(prof.get(view_type, 0)) + 1
    try:
        last_seq = 0
        while running:
            async with st["cond"]:
                await st["cond"].wait_for(lambda: (st["seq"] != last_seq) or (not running))
                seq = st["seq"]
                frame_bytes = st["jpeg"][profile][view_type]

            if not frame_bytes:
                await asyncio.sleep(0.01)
                continue

            last_seq = seq
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
    finally:
        try:
            async with st["cond"]:
                prof = st["watchers"].get(profile)
                if isinstance(prof, dict):
                    prof[view_type] = max(0, int(prof.get(view_type, 0)) - 1)
        except Exception:
            pass


async def _broadcast_fps_loop():
    global running, stream_state
    while running:
        now = time.time()
        cameras_payload = {}
        for cam_id, st in stream_state.items():
            stats = dict(st.get("stats", {}))
            if now - float(stats.get("updated_at", 0.0)) > 2.0:
                stats["camera_fps"] = 0.0
                stats["capture_fps"] = 0.0
                stats["stream_fps"] = 0.0
            if now - float(stats.get("infer_updated_at", 0.0)) > 2.0:
                stats["infer_fps"] = 0.0
            cameras_payload[int(cam_id)] = stats
        try:
            await sio.emit("camera_fps", {"cameras": cameras_payload})
        except Exception:
            pass
        await asyncio.sleep(0.5)


def _get_device_lock(camera_index: int) -> asyncio.Lock:
    global device_op_locks
    lock = device_op_locks.get(int(camera_index))
    if lock is None:
        lock = asyncio.Lock()
        device_op_locks[int(camera_index)] = lock
    return lock


@app.get("/video_feed/{camera_id}")
async def video_feed(
    camera_id: int = Path(..., ge=0, le=3),
    type: str = "detect",
    profile: str = "grid",
):
    """
    Video feed endpoint.
    type: "detect" (default) -> draws bounding boxes
          "raw" -> shows clean video without boxes
    """
    return StreamingResponse(
        _stream_generator(camera_id, profile=profile, view_type=type),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/status")
async def get_status():
    status_data = {
        "model_loaded": detector.is_loaded() if detector else False,
        "model_type": detector.current_model_type if detector else "none", # Return actual loaded type
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


# --- Camera Discovery & Management APIs ---

@app.get("/models")
async def list_models():
    global detector
    try:
        if not detector:
            detector = DefectDetector()
        models = detector.list_available_models()
        return {
            "models": models,
            "default_model": "yolo26s",
            "active_model_name": detector.model_name,
            "active_model_type": detector.current_model_type,
            "active_device": detector.device,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/cameras/discover")
async def discover_cameras():
    global sdk_op_lock
    try:
        if sdk_op_lock is None:
            sdk_op_lock = asyncio.Lock()
        async with sdk_op_lock:
            cams = await asyncio.to_thread(get_available_cameras)
        return {"cameras": cams, **get_hik_sdk_status()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class ConnectRequest(BaseModel):
    camera_index: int  # The index from discovery list

@app.post("/cameras/{slot_id}/connect")
async def connect_camera(request: ConnectRequest, slot_id: int = Path(..., ge=0, le=3)):
    global cameras, persisted_settings, sdk_op_lock, camera_detections, stream_state, slot_op_locks
    if slot_id not in cameras:
        return JSONResponse(status_code=404, content={"error": "Invalid slot"})

    if sdk_op_lock is None:
        sdk_op_lock = asyncio.Lock()
    slot_lock = slot_op_locks.get(slot_id) if isinstance(slot_op_locks, dict) else None
    if slot_lock is None:
        slot_lock = asyncio.Lock()
        slot_op_locks[slot_id] = slot_lock

    device_lock = _get_device_lock(request.camera_index)

    async with slot_lock:
        async with device_lock:
            async with sdk_op_lock:
                for s_id, cam_driver in cameras.items():
                    if s_id != slot_id and cam_driver.connected and cam_driver.index == request.camera_index:
                        error_msg = f"Camera {request.camera_index} is already used by Slot {s_id}"
                        await broadcast_log("错误", error_msg, "high")
                        return JSONResponse(status_code=400, content={"error": error_msg})

                cam = cameras[slot_id]

                if cam.connected:
                    await asyncio.to_thread(cam.release)

                camera_detections[slot_id] = []
                st = stream_state.get(slot_id)
                if st:
                    async with st["cond"]:
                        st["seq"] += 1
                        st["jpeg"]["grid"]["raw"] = None
                        st["jpeg"]["grid"]["detect"] = None
                        st["jpeg"]["full"]["raw"] = None
                        st["jpeg"]["full"]["detect"] = None
                        st["stats"]["updated_at"] = time.time()
                        st["cond"].notify_all()

                cam.index = request.camera_index

                success = False
                last_err = None
                for attempt in range(3):
                    success = await asyncio.to_thread(cam.connect)
                    if success:
                        break
                    last_err = getattr(cam, "last_error_ret", None)
                    if last_err == 0x80000203:
                        await asyncio.to_thread(cam.release)
                        await asyncio.sleep(0.2 * (attempt + 1))
                        continue
                    break

                if success:
                    try:
                        cfg = persisted_settings.get("camera_params", {}).get(str(slot_id), {})
                        exposure_time_us = cfg.get("exposure_time_us")
                        gain_db = cfg.get("gain_db")
                        ok, msg = await asyncio.to_thread(cam.apply_params, exposure_time_us, gain_db)
                        if ok:
                            await broadcast_log("配置", f"Slot {slot_id} 相机参数已应用: {msg}", "info")
                        else:
                            await broadcast_log("错误", f"Slot {slot_id} 相机参数应用失败: {msg}", "high")
                    except Exception as e:
                        await broadcast_log("错误", f"Slot {slot_id} 相机参数应用异常: {e}", "high")
                    await broadcast_log("系统", f"Slot {slot_id} 已连接到相机 {cam.index}", "info")
                    return {"status": "connected", "slot": slot_id, "camera_index": cam.index}

                await asyncio.to_thread(cam.release)
                await broadcast_log("错误", f"Slot {slot_id} 连接失败", "high")
                if last_err == 0x80000203:
                    return JSONResponse(status_code=409, content={"error": "Device occupied, please retry"})
                return JSONResponse(status_code=500, content={"error": "Failed to connect"})

@app.post("/cameras/{slot_id}/disconnect")
async def disconnect_camera(slot_id: int = Path(..., ge=0, le=3)):
    global cameras, camera_detections, sdk_op_lock, stream_state, slot_op_locks
    if sdk_op_lock is None:
        sdk_op_lock = asyncio.Lock()
    slot_lock = slot_op_locks.get(slot_id) if isinstance(slot_op_locks, dict) else None
    if slot_lock is None:
        slot_lock = asyncio.Lock()
        slot_op_locks[slot_id] = slot_lock

    async with slot_lock:
        if slot_id in cameras:
            async with sdk_op_lock:
                await asyncio.to_thread(cameras[slot_id].release)
            camera_detections[slot_id] = []
            st = stream_state.get(slot_id)
            if st:
                async with st["cond"]:
                    st["seq"] += 1
                    st["jpeg"]["grid"]["raw"] = None
                    st["jpeg"]["grid"]["detect"] = None
                    st["jpeg"]["full"]["raw"] = None
                    st["jpeg"]["full"]["detect"] = None
                    st["stats"]["updated_at"] = time.time()
                    st["cond"].notify_all()
            await broadcast_log("系统", f"Slot {slot_id} 已断开连接", "info")
        return {"status": "disconnected", "slot": slot_id}


@app.get("/config/mode")
async def get_mode():
    global is_manual_mode
    return {"manual_mode": is_manual_mode}

class ModeRequest(BaseModel):
    manual_mode: bool

@app.post("/config/mode")
async def set_mode(request: ModeRequest):
    global is_manual_mode, auto_inference, persisted_settings
    is_manual_mode = request.manual_mode
    auto_inference = not is_manual_mode

    try:
        persisted_settings = load_settings()
        persisted_settings["manual_mode"] = bool(is_manual_mode)
        save_settings(persisted_settings)
    except Exception:
        pass
    
    mode_str = "手动触发模式" if is_manual_mode else "实时检测模式"
    await broadcast_log("模式切换", f"系统已切换至: {mode_str}", "info")
    return {"status": "updated", "manual_mode": is_manual_mode}

@app.post("/trigger/detect")
async def trigger_detect():
    """Manually trigger detection on all connected cameras"""
    global cameras, detector
    
    if not detector:
        return JSONResponse(status_code=500, content={"error": "Detector not loaded"})
    
    connected = []
    for slot_id, cam in cameras.items():
        if cam.connected:
            connected.append((slot_id, cam))

    if not connected:
        await broadcast_log("手动检测", "未发现活跃的摄像头连接", "medium")
        return {"message": "No active cameras"}

    frames = []
    for slot_id, cam in connected:
        frame = cam.get_frame(raw=True)
        if frame is not None:
            frames.append((slot_id, frame))

    if not frames:
        await broadcast_log("手动检测", "未获取到有效帧", "medium")
        return {"message": "No valid frames"}

    sem = asyncio.Semaphore(2)

    async def _run_one(slot_id: int, frame):
        async with sem:
            t0 = time.perf_counter()
            results, annotated_frame = await asyncio.to_thread(detector.predict, frame)
            dt_ms = (time.perf_counter() - t0) * 1000.0

            det_count = len(results)
            ts = time.time_ns()
            filename = f"manual_trigger_slot{slot_id}_{ts}.jpg"
            filepath = os.path.join(HISTORY_DIR, filename)
            await asyncio.to_thread(cv2.imwrite, filepath, annotated_frame)
            image_url = f"http://localhost:8000/history/{filename}"

            msg_type = "high" if det_count > 0 else "info"
            await broadcast_log(
                f"手动抓拍 (Slot {slot_id})",
                f"耗时 {dt_ms:.1f}ms, 检测到 {det_count} 个目标 | Model={detector.model_name}/{detector.current_model_type} ({detector.device}) | conf={detector.conf}, imgsz={detector.imgsz}",
                msg_type,
                attachment=image_url,
            )

            return {"slot": slot_id, "detections": det_count, "image_url": image_url}

    results_summary = [r for r in await asyncio.gather(*[_run_one(s, f) for s, f in frames]) if r]
    
    if not results_summary:
        await broadcast_log("手动检测", "未发现活跃的摄像头连接", "medium")
        return {"message": "No active cameras"}
        
    return {"message": "Detection completed", "results": results_summary}


# --- Logs and Settings ---


@app.get("/logs")
async def get_logs(lines: int = 50):
    try:
        if not os.path.exists(EVENTS_LOG_PATH):
            return {"logs": []}

        with open(EVENTS_LOG_PATH, "r", encoding="utf-8") as f:
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
    log_interval: int = 10
    model_type: str = "auto" # pt, onnx, openvino, auto
    model_name: str = "yolo26s"
    camera_params: Dict[str, Dict[str, float]] = {}
    scene_mode: str | None = None


@app.get("/config/settings")
async def get_settings():
    global log_cooldown, persisted_settings
    settings = load_settings()
    settings["log_interval"] = int(log_cooldown)
    if detector:
        settings["conf"] = detector.conf
        settings["imgsz"] = detector.imgsz
        settings["active_model_type"] = detector.current_model_type
        settings["active_device"] = detector.device
        settings["active_model_name"] = detector.model_name

    if isinstance(settings.get("camera_params"), dict):
        for slot_id, cam in cameras.items():
            key = str(slot_id)
            if key in settings["camera_params"] and isinstance(settings["camera_params"][key], dict):
                try:
                    cam.exposure_time_us = float(settings["camera_params"][key].get("exposure_time_us", cam.exposure_time_us))
                    cam.gain_db = float(settings["camera_params"][key].get("gain_db", cam.gain_db))
                except Exception:
                    pass

    persisted_settings = settings
    return settings


class SceneRequest(BaseModel):
    scene_mode: str


@app.get("/config/scene")
async def get_scene():
    settings = load_settings()
    return {"scene_mode": settings.get("scene_mode", "day")}


@app.post("/config/scene")
async def set_scene(request: SceneRequest):
    global persisted_settings
    mode = request.scene_mode
    if mode not in ("day", "night"):
        return JSONResponse(status_code=400, content={"error": "Invalid scene_mode"})

    persisted_settings = load_settings()
    persisted_settings["scene_mode"] = mode
    save_settings(persisted_settings)

    await broadcast_log("配置", f"场景模式已切换: {mode}", "medium")
    return {"status": "updated", "scene_mode": mode}


@app.post("/config/settings")
async def update_settings(settings: SettingsModel):
    global log_cooldown, persisted_settings, model_reload_lock, model_reloading
    
    # Update log interval
    log_cooldown = float(settings.log_interval)
    persisted_settings = load_settings()
    persisted_settings["log_interval"] = int(settings.log_interval)
    persisted_settings["model_type"] = settings.model_type
    persisted_settings["model_name"] = settings.model_name
    persisted_settings["conf"] = float(settings.conf)
    persisted_settings["imgsz"] = int(settings.imgsz)
    if settings.scene_mode in ("day", "night"):
        persisted_settings["scene_mode"] = settings.scene_mode

    if isinstance(settings.camera_params, dict) and settings.camera_params:
        if not isinstance(persisted_settings.get("camera_params"), dict):
            persisted_settings["camera_params"] = default_settings()["camera_params"]
        for slot_key, v in settings.camera_params.items():
            if not isinstance(v, dict):
                continue
            if slot_key not in persisted_settings["camera_params"]:
                continue
            if "exposure_time_us" in v:
                persisted_settings["camera_params"][slot_key]["exposure_time_us"] = float(v["exposure_time_us"])
            if "gain_db" in v:
                persisted_settings["camera_params"][slot_key]["gain_db"] = float(v["gain_db"])

    save_settings(persisted_settings)
    
    if detector:
        # Check if model switch requested
        target_type = settings.model_type
        target_name = settings.model_name
        
        needs_reload = False
        if target_type == "auto":
            try:
                selected = detector._select_best_available_model(target_name)
                if selected is None:
                    needs_reload = detector.current_model_type not in ("openvino", "onnx", "pt")
                else:
                    best_path, best_type = selected
                    needs_reload = (
                        (best_type != detector.current_model_type)
                        or (os.path.abspath(best_path) != os.path.abspath(detector.model_path))
                        or (str(target_name) != str(detector.model_name))
                    )
            except Exception:
                needs_reload = detector.current_model_type not in ("openvino", "onnx", "pt")
        else:
            needs_reload = (target_type != detector.current_model_type) or (str(target_name) != str(detector.model_name))
        
        if needs_reload:
            if model_reload_lock is None:
                model_reload_lock = asyncio.Lock()
            async with model_reload_lock:
                model_reloading = True
                await broadcast_log(
                    "配置",
                    f"开始切换模型: request=({target_name}/{target_type}) | current={detector.model_name}/{detector.current_model_type} ({detector.device})",
                    "medium",
                )
                try:
                    success, msg = await asyncio.to_thread(detector.reload_model, target_type, target_name)
                finally:
                    model_reloading = False
            if success:
                await broadcast_log(
                    "配置",
                    f"模型已切换: name={detector.model_name}, type={detector.current_model_type}, device={detector.device} | request=({target_name}/{target_type}) | {msg}",
                    "medium",
                )
            else:
                await broadcast_log("错误", f"切换失败: {msg}", "high")

        await asyncio.to_thread(detector.update_settings, conf=settings.conf, imgsz=settings.imgsz)

        applied = []
        for slot_id, cam in cameras.items():
            if not cam.connected:
                continue
            slot_key = str(slot_id)
            cfg = persisted_settings.get("camera_params", {}).get(slot_key, {})
            exposure_time_us = cfg.get("exposure_time_us")
            gain_db = cfg.get("gain_db")
            ok, msg = await asyncio.to_thread(cam.apply_params, exposure_time_us, gain_db)
            applied.append((slot_id, ok, msg))
        for slot_id, ok, msg in applied:
            await broadcast_log(
                "配置",
                f"Slot {slot_id} 相机参数应用: {'OK' if ok else 'FAIL'} ({msg})",
                "info" if ok else "high",
            )

        await broadcast_log(
            "配置",
            f"系统参数已更新: Conf={settings.conf}, Size={settings.imgsz}, Interval={log_cooldown}s | ActiveModel={detector.model_name}/{detector.current_model_type} ({detector.device})",
            "medium",
        )
        return {"status": "updated", "conf": detector.conf, "imgsz": detector.imgsz, "log_interval": log_cooldown}
    
    return JSONResponse(status_code=500, content={"error": "Detector not initialized"})


if __name__ == "__main__":
    uvicorn.run(final_app, host="127.0.0.1", port=8000, reload=False)
