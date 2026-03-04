import argparse
import os
import inspect
import datetime


def export_openvino_from_onnx(
    onnx_path: str,
    out_dir: str,
    input_shape: str | None,
    compress_to_fp16: bool,
):
    from openvino.tools.ovc import convert_model
    from openvino.runtime import serialize

    if not os.path.exists(onnx_path):
        raise FileNotFoundError(f"ONNX not found: {onnx_path}")

    os.makedirs(out_dir, exist_ok=True)
    xml_path = os.path.join(out_dir, "best.xml")
    bin_path = os.path.join(out_dir, "best.bin")

    shape = None
    if input_shape:
        parts = [int(x) for x in input_shape.split(",")]
        if len(parts) != 4:
            raise ValueError("input-shape must be like: 1,3,640,640")
        shape = parts

    sig = inspect.signature(convert_model)
    kwargs = {}
    if "compress_to_fp16" in sig.parameters:
        kwargs["compress_to_fp16"] = bool(compress_to_fp16)

    ov_model = convert_model(onnx_path, **kwargs)
    if shape is not None:
        try:
            input_name = ov_model.inputs[0].get_any_name()
            ov_model.reshape({input_name: shape})
        except Exception:
            pass

    serialize(ov_model, xml_path, bin_path)
    _write_metadata_yaml(out_dir=out_dir, shape=shape, half=compress_to_fp16)
    return xml_path


def _write_metadata_yaml(out_dir: str, shape: list[int] | None, half: bool):
    metadata_path = os.path.join(out_dir, "metadata.yaml")

    imgsz = [640, 640]
    batch = 1
    if shape and len(shape) == 4:
        batch = int(shape[0])
        imgsz = [int(shape[2]), int(shape[3])]

    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                old = f.read()
            names_block = None
            if "\nnames:\n" in old:
                names_block = old.split("\nnames:\n", 1)[1]
                names_block = names_block.split("\nargs:\n", 1)[0]
                names_block = "names:\n" + names_block.strip("\n") + "\n"
        except Exception:
            names_block = None
    else:
        names_block = None

    if not names_block:
        names_block = "names:\n  0: defects\n"

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    content = (
        f"author: Ultralytics\n"
        f"date: '{now}'\n"
        f"task: detect\n"
        f"stride: 32\n"
        f"batch: {batch}\n"
        f"imgsz:\n"
        f"- {imgsz[0]}\n"
        f"- {imgsz[1]}\n"
        f"{names_block}"
        f"args:\n"
        f"  batch: {batch}\n"
        f"  half: {str(bool(half)).lower()}\n"
        f"  int8: false\n"
        f"  dynamic: false\n"
        f"  nms: false\n"
        f"channels: 3\n"
        f"end2end: false\n"
    )

    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--onnx", default="models/best.onnx")
    parser.add_argument("--out", default="models/best_openvino_model")
    parser.add_argument("--input-shape", default="1,3,640,640")
    parser.add_argument("--fp32", action="store_true")
    args = parser.parse_args()

    xml_path = export_openvino_from_onnx(
        onnx_path=args.onnx,
        out_dir=args.out,
        input_shape=args.input_shape,
        compress_to_fp16=not bool(args.fp32),
    )
    print(f"Exported OpenVINO IR: {xml_path}")


if __name__ == "__main__":
    main()
