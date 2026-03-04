import json
import os
import sys
from typing import Any, Dict


def _config_path() -> str:
    explicit = os.environ.get("HK_TAURI_CONFIG_PATH")
    if explicit:
        return explicit

    base_dir = os.environ.get("HK_TAURI_DATA_DIR") or os.environ.get("HK_TAURI_CONFIG_DIR")
    if base_dir:
        return os.path.join(base_dir, "config.json")

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, "HK_Tauri_Data", "config.json")

    appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if appdata:
        return os.path.join(appdata, "HK_Tauri_Data", "config.json")

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(backend_dir, "config.json")


def default_settings() -> Dict[str, Any]:
    return {
        "conf": 0.25,
        "imgsz": 640,
        "log_interval": 10,
        "model_type": "auto",
        "model_name": "yolo26s",
        "manual_mode": True,
        "scene_mode": "day",
        "camera_params": {
            "0": {"exposure_time_us": 50000.0, "gain_db": 0.0},
            "1": {"exposure_time_us": 50000.0, "gain_db": 0.0},
            "2": {"exposure_time_us": 50000.0, "gain_db": 0.0},
            "3": {"exposure_time_us": 50000.0, "gain_db": 0.0},
        },
    }


def load_settings() -> Dict[str, Any]:
    path = _config_path()
    data = default_settings()
    if not os.path.exists(path):
        try:
            save_settings(data)
        except Exception:
            pass
        return data

    try:
        with open(path, "r", encoding="utf-8") as f:
            on_disk = json.load(f) or {}
        if isinstance(on_disk, dict):
            data.update({k: v for k, v in on_disk.items() if k in data})
            if isinstance(on_disk.get("camera_params"), dict):
                merged = data["camera_params"]
                for k, v in on_disk["camera_params"].items():
                    if k not in merged or not isinstance(v, dict):
                        continue
                    merged[k] = {
                        "exposure_time_us": float(v.get("exposure_time_us", merged[k]["exposure_time_us"])),
                        "gain_db": float(v.get("gain_db", merged[k]["gain_db"])),
                    }
                data["camera_params"] = merged
    except Exception:
        return data

    if not data.get("model_type"):
        data["model_type"] = "auto"

    if not data.get("model_name"):
        data["model_name"] = "yolo26s"

    if data.get("scene_mode") not in ("day", "night"):
        data["scene_mode"] = "day"

    return data


def save_settings(settings: Dict[str, Any]) -> None:
    path = _config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
