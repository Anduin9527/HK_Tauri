import os
import sys
import threading

os.environ.setdefault("ULTRALYTICS_AUTOINSTALL", "0")
os.environ.setdefault("YOLO_AUTOINSTALL", "0")

from ultralytics import YOLO


class DefectDetector:
    def __init__(self, model_path=None):
        self.lock = threading.Lock()
        self.current_model_type = "unknown"
        self.model_name = "yolo26s"
        self._backend_dir = os.path.dirname(os.path.abspath(__file__))
        self._models_dir_candidates = [
            os.path.join(self._backend_dir, "models"),
            os.path.join(os.path.dirname(self._backend_dir), "models"),
        ]
        
        if model_path is None:
            selected = self._select_best_available_model(self.model_name)
            if selected is None:
                print("Warning: No model found in default locations (best.pt|best.onnx)")
                self.model_path = os.path.join(self._backend_dir, "models", "best.pt")
                self.current_model_type = "pt"
            else:
                self.model_path, self.current_model_type = selected
        else:
            self.model_path = os.path.abspath(model_path)
            self.current_model_type = self._infer_type_from_path(self.model_path)
            inferred = self._infer_name_from_path(self.model_path)
            if inferred:
                self.model_name = inferred

        self.model = None
        self.device = "cpu"
        
        # Settings
        self.conf = 0.25
        self.imgsz = 640

        self.load_model()

    def _infer_type_from_path(self, path: str) -> str:
        if path.endswith(".onnx"):
            return "onnx"
        if path.endswith(".pt"):
            return "pt"
        return "unknown"

    def _infer_name_from_path(self, path: str) -> str | None:
        if os.path.isdir(path):
            return None
        base = os.path.basename(path.rstrip(os.sep))
        if base.endswith(".pt") or base.endswith(".onnx"):
            base = base.rsplit(".", 1)[0]
        if base == "best":
            return "yolo26s"
        return base if base else None

    def _get_models_dir(self) -> str | None:
        for d in self._models_dir_candidates:
            if os.path.isdir(d):
                return d
        return None

    def _find_prefixed_model(self, models_dir: str, prefix: str):
        onnx_candidates = []
        pt_candidates = []
        try:
            for name in os.listdir(models_dir):
                if not name.startswith(f"{prefix}_"):
                    continue
                full = os.path.join(models_dir, name)
                if not os.path.isfile(full):
                    continue
                if name.endswith(".onnx"):
                    onnx_candidates.append(full)
                elif name.endswith(".pt"):
                    pt_candidates.append(full)
        except Exception:
            return []

        def _pick_latest(paths):
            if not paths:
                return None
            paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return paths[0]

        result = []
        latest_onnx = _pick_latest(onnx_candidates)
        latest_pt = _pick_latest(pt_candidates)
        if latest_onnx:
            result.append((latest_onnx, "onnx"))
        if latest_pt:
            result.append((latest_pt, "pt"))
        return result

    def _select_best_available_model(self, model_name: str):
        models_dir = self._get_models_dir()
        if not models_dir:
            return None

        candidates = []

        if model_name in ("yolo26s", "yolo26n"):
            prefix_matches = self._find_prefixed_model(models_dir, model_name)
            if prefix_matches:
                candidates.extend(prefix_matches)

        if model_name:
            candidates.extend(
                [
                    (os.path.join(models_dir, f"{model_name}.onnx"), "onnx"),
                    (os.path.join(models_dir, f"{model_name}.pt"), "pt"),
                ]
            )

        if model_name == "yolo26s" or not model_name:
            candidates.extend(
                [
                    (os.path.join(models_dir, "best.onnx"), "onnx"),
                    (os.path.join(models_dir, "best.pt"), "pt"),
                ]
            )
        elif model_name != "yolo26s":
            candidates.extend(
                [
                    (os.path.join(models_dir, "best.onnx"), "onnx"),
                    (os.path.join(models_dir, "best.pt"), "pt"),
                ]
            )

        for path, t in candidates:
            if os.path.exists(path):
                return os.path.abspath(path), t

        return None

    def list_available_models(self):
        models_dir = self._get_models_dir()
        if not models_dir:
            return []

        found = {}
        for name in os.listdir(models_dir):
            full = os.path.join(models_dir, name)
            if os.path.isfile(full):
                if name.endswith(".pt") or name.endswith(".onnx"):
                    base = name.rsplit(".", 1)[0]
                    if base == "best":
                        base = "yolo26s"
                    info = found.setdefault(base, {"name": base, "pt": False, "onnx": False})
                    if name.endswith(".pt"):
                        info["pt"] = True
                    if name.endswith(".onnx"):
                        info["onnx"] = True

        result = list(found.values())
        result.sort(key=lambda x: x["name"])
        return result

    def reload_model(self, model_type, model_name: str | None = None):
        new_path = None
        resolved_type = model_type
        if model_name:
            self.model_name = str(model_name)
        selected_best = None

        if model_type == "auto":
            selected_best = self._select_best_available_model(self.model_name)
            if selected_best is not None:
                new_path, resolved_type = selected_best
        else:
            models_dir = self._get_models_dir()
            if models_dir:
                if model_type == "onnx":
                    if self.model_name in ("yolo26s", "yolo26n"):
                        for path, t in self._find_prefixed_model(models_dir, self.model_name):
                            if t == "onnx" and os.path.exists(path):
                                new_path = os.path.abspath(path)
                                break
                    if not new_path:
                        candidate = os.path.join(models_dir, f"{self.model_name}.onnx")
                        if os.path.exists(candidate):
                            new_path = os.path.abspath(candidate)
                    if not new_path:
                        candidate = os.path.join(models_dir, "best.onnx")
                        if os.path.exists(candidate):
                            new_path = os.path.abspath(candidate)
                elif model_type == "pt":
                    if self.model_name in ("yolo26s", "yolo26n"):
                        for path, t in self._find_prefixed_model(models_dir, self.model_name):
                            if t == "pt" and os.path.exists(path):
                                new_path = os.path.abspath(path)
                                break
                    if not new_path:
                        candidate = os.path.join(models_dir, f"{self.model_name}.pt")
                        if os.path.exists(candidate):
                            new_path = os.path.abspath(candidate)
                    if not new_path:
                        candidate = os.path.join(models_dir, "best.pt")
                        if os.path.exists(candidate):
                            new_path = os.path.abspath(candidate)
        
        if new_path:
            try:
                if os.path.abspath(new_path) == os.path.abspath(self.model_path) and resolved_type == self.current_model_type:
                    return True, f"no-op: {self.model_name}/{resolved_type} @ {new_path}"
            except Exception:
                pass
            with self.lock:
                print(f"Switching model to: {new_path}")
                self.model_path = new_path
                self.current_model_type = resolved_type
                self.model = None
                self.load_model()
            if model_type == "auto":
                return True, f"auto resolved to {self.model_name}/{resolved_type} @ {new_path}"
            return True, f"set to {self.model_name}/{resolved_type} @ {new_path}"
        else:
            print(f"Model type {model_type} not found.")
            return False, f"Model file for {model_type} not found"

    def load_model(self):
        print(f"Loading YOLO model: {self.model_path}...")

        self.model = None
        load_errors = []

        models_dir = self._get_models_dir()

        raw_attempts = []
        if self.model_path:
            raw_attempts.append((self.model_path, self._infer_type_from_path(self.model_path)))

        if models_dir:
            if self.model_name in ("yolo26s", "yolo26n"):
                raw_attempts.extend(self._find_prefixed_model(models_dir, self.model_name))
            if self.model_name:
                raw_attempts.extend(
                    [
                        (os.path.join(models_dir, f"{self.model_name}.onnx"), "onnx"),
                        (os.path.join(models_dir, f"{self.model_name}.pt"), "pt"),
                    ]
                )
            raw_attempts.extend(
                [
                    (os.path.join(models_dir, "best.onnx"), "onnx"),
                    (os.path.join(models_dir, "best.pt"), "pt"),
                ]
            )

        attempts = []
        seen = set()
        for path, model_type in raw_attempts:
            if not path:
                continue
            key = (os.path.abspath(path), model_type)
            if key in seen:
                continue
            seen.add(key)
            attempts.append((path, model_type))

        for path, model_type in attempts:
            try:
                if model_type == "onnx" or path.endswith(".onnx"):
                    print(f"Loading ONNX model: {path}...")
                    model = YOLO(path, task="detect")
                    device = "cpu"
                    resolved_type = "onnx"
                elif model_type == "pt" or path.endswith(".pt"):
                    print(f"Loading PyTorch model: {path}...")
                    model = YOLO(path, task="detect")
                    device = "cpu"
                    resolved_type = "pt"
                else:
                    raise RuntimeError(f"Unsupported model type: {model_type}")

                self.model = model
                self.device = device
                self.current_model_type = resolved_type
                self.model_path = path
                inferred = self._infer_name_from_path(path)
                if inferred:
                    self.model_name = inferred

                self._warmup_or_raise()
                return
            except Exception as e:
                load_errors.append((path, str(e)))
                self.model = None

        print("Error loading model. Attempts:")
        for p, err in load_errors:
            print(f" - {p}: {err}")
        raise RuntimeError("All model load attempts failed.")

    def _warmup_or_raise(self):
        try:
            import numpy as np
            dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
            _ = self.model(dummy, verbose=False, conf=self.conf, imgsz=self.imgsz)
            print("Model warmup completed.")
        except Exception as e:
            raise RuntimeError(f"Model warmup failed: {e}")

    def update_settings(self, conf=None, imgsz=None):
        with self.lock:
            if conf is not None:
                self.conf = float(conf)
            if imgsz is not None:
                self.imgsz = int(imgsz)
            print(f"Detector settings updated: conf={self.conf}, imgsz={self.imgsz}")

    def predict(self, frame, return_annotated=True):
        with self.lock:
            if self.model is None:
                return [], frame

            # Run inference with dynamic settings
            # Ultralytics handles resizing internally via 'imgsz' argument
            # It will resize input 'frame' to 'imgsz' (e.g. 640) for inference,
            # and then automatically scale bounding boxes back to original 'frame' size.
            try:
                if frame is not None and hasattr(frame, "ndim") and frame.ndim == 2:
                    import cv2
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                elif frame is not None and hasattr(frame, "shape") and len(frame.shape) == 3 and frame.shape[2] == 1:
                    import cv2
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

                results = self.model(frame, verbose=False, conf=self.conf, imgsz=self.imgsz)
            except Exception as e:
                print(
                    f"Inference error with settings conf={self.conf}, imgsz={self.imgsz}: {e}"
                )
                # Fallback
                results = self.model(frame, verbose=False)

            detections = []
            # Extract raw data
            for box in results[0].boxes:
                detections.append(
                    {
                        "class": int(box.cls),
                        "label": results[0].names[int(box.cls)],
                        "conf": float(box.conf),
                        "bbox": box.xywh.tolist(), # xywh in original frame coordinates
                        "xyxy": box.xyxy.tolist(), # xyxy for drawing
                    }
                )
                
            annotated_frame = None
            if return_annotated:
                # Plot results on original frame
                # Ultralytics results[0].plot() returns BGR numpy array of same size as input
                annotated_frame = results[0].plot()

            return detections, annotated_frame

    def is_loaded(self):
        return self.model is not None
