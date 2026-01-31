import os
from ultralytics import YOLO


class DefectDetector:
    def __init__(self, model_path="models/best.onnx"):
        self.model_path = model_path
        self.model = None
        self.device = "cpu"  # Default

        # Settings
        self.conf = 0.25
        self.imgsz = 640

        self.load_model()

    def load_model(self):
        print(f"Loading YOLO model: {self.model_path}...")

        try:
            if self.model_path.endswith(".onnx"):
                print(f"Loading ONNX model: {self.model_path}...")
                # Ultralytics supports loading .onnx directly
                self.model = YOLO(self.model_path, task="detect")
                self.device = "cpu"  # ONNX typically runs on CPU or specific provider
            else:
                print("Loading standard PyTorch model...")
                self.model = YOLO(self.model_path)

                # Check for OpenVINO export if available
                openvino_path = self.model_path.replace(".pt", "_openvino_model")
                if os.path.exists(openvino_path):
                    print(f"Found OpenVINO model at {openvino_path}, loading...")
                    self.model = YOLO(openvino_path, task="detect")
                    self.device = "openvino"

        except Exception as e:
            print(f"Error loading model: {e}")
            print("Fallback to standard model")
            self.model = YOLO(self.model_path)

    def update_settings(self, conf=None, imgsz=None):
        if conf is not None:
            self.conf = float(conf)
        if imgsz is not None:
            self.imgsz = int(imgsz)
        print(f"Detector settings updated: conf={self.conf}, imgsz={self.imgsz}")

    def predict(self, frame):
        if self.model is None:
            return [], frame

        # Run inference with dynamic settings
        try:
            results = self.model(frame, verbose=False, conf=self.conf, imgsz=self.imgsz)
        except Exception as e:
            print(
                f"Inference error with settings conf={self.conf}, imgsz={self.imgsz}: {e}"
            )
            # Fallback
            results = self.model(frame, verbose=False)

        # Plot results on frame
        # Ultralytics results[0].plot() returns BGR numpy array
        annotated_frame = results[0].plot()

        detections = []
        # Extract raw data if needed
        for box in results[0].boxes:
            detections.append(
                {
                    "class": int(box.cls),
                    "conf": float(box.conf),
                    "bbox": box.xywh.tolist(),
                }
            )

        return detections, annotated_frame

    def is_loaded(self):
        return self.model is not None
