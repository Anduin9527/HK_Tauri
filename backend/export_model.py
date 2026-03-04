import os
from ultralytics import YOLO
import argparse

def export_model(
    model_path: str = "models/best.pt",
    format: str = "onnx",
    imgsz: int = 640,
    batch: int = 1,
    int8: bool = False,
    half: bool = True,
    data: str | None = None,
):
    """
    Exports the YOLO model to the specified format.
    
    Args:
        model_path (str): Path to the .pt model file.
        format (str): Export format (e.g., 'onnx').
        imgsz (int): Input image size.
        batch (int): Export batch size. Prefer 1 for low-latency multi-camera pipelines.
        int8 (bool): Enable INT8 quantization (recommend providing representative 'data').
        half (bool): Enable FP16 quantization.
        data (str|None): Dataset yaml for INT8 calibration.
    """
    if not os.path.exists(model_path):
        print(f"Error: Model file '{model_path}' not found.")
        return

    print(f"Loading model: {model_path}...")
    model = YOLO(model_path)
    
    print(f"Starting export to {format} (imgsz={imgsz}, batch={batch}, INT8={int8}, FP16={half})...")
    
    # Export args
    kwargs = {"format": format, "imgsz": int(imgsz), "batch": int(batch)}
    if int8:
        kwargs["int8"] = True
        if data:
            kwargs["data"] = data
        else:
            kwargs["data"] = "coco8.yaml"
    if half and not int8:
        kwargs["half"] = True
        
    try:
        exported_path = model.export(**kwargs)
        print(f"Export successful! Saved to: {exported_path}")
    except Exception as e:
        print(f"Export failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/best.pt")
    parser.add_argument("--format", default="onnx")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--int8", action="store_true")
    parser.add_argument("--half", action="store_true")
    parser.add_argument("--data", default=None)
    args = parser.parse_args()

    half = bool(args.half)
    if not args.int8 and not args.half:
        half = True

    export_model(
        model_path=args.model,
        format=args.format,
        imgsz=args.imgsz,
        batch=args.batch,
        int8=bool(args.int8),
        half=half,
        data=args.data,
    )
