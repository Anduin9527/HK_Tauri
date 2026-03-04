import datetime
import zipfile
from pathlib import Path


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _p(text: str, bold: bool = False, size: int | None = None) -> str:
    rpr = ""
    if bold or size:
        inner = ""
        if bold:
            inner += "<w:b/>"
        if size:
            inner += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
        rpr = f"<w:rPr>{inner}</w:rPr>"
    return (
        "<w:p><w:r>"
        + rpr
        + f'<w:t xml:space="preserve">{_xml_escape(text)}</w:t>'
        + "</w:r></w:p>"
    )


def _bullet(text: str) -> str:
    return _p(f"• {text}")


def _document_xml(items: list[tuple[str, str]]) -> str:
    ns_w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    parts: list[str] = []
    for kind, txt in items:
        if kind == "title":
            parts.append(_p(txt, bold=True, size=36))
        elif kind == "h1":
            parts.append(_p(txt, bold=True, size=28))
        elif kind == "h2":
            parts.append(_p(txt, bold=True, size=24))
        elif kind == "li":
            parts.append(_bullet(txt))
        else:
            parts.append(_p(txt))

    body = (
        "".join(parts)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        + '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        + 'w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{ns_w}">
  <w:body>
    {body}
  </w:body>
</w:document>
"""


def generate_docx(out_path: Path) -> Path:
    manual: list[tuple[str, str]] = [
        ("title", "行李缺陷检测系统 使用手册（简明版）"),
        ("p", "适用对象：首次上手的操作人员。"),
        ("p", "软件组成：桌面端界面 + 本机后端服务（127.0.0.1:8000）。"),
        ("h1", "1. 启动与数据保存"),
        ("p", "双击桌面图标启动；软件会自动拉起后端服务。"),
        ("p", "默认数据目录：安装目录旁的 HK_Tauri_Data（若安装目录不可写，会自动回退到 AppData）。"),
        ("p", "目录结构："),
        ("li", r"HK_Tauri_Data\\history\\：缺陷截图/原图/events.log"),
        ("li", r"HK_Tauri_Data\\config.json：系统配置"),
        ("li", r"HK_Tauri_Data\\backend.log：后端运行日志（排障用）"),
        ("p", "查看实际落盘路径：在浏览器打开 http://127.0.0.1:8000/paths。"),
        ("h1", "2. 界面入口"),
        ("li", "实时监控：连接相机、查看视频流、自动/手动检测、全屏查看"),
        ("li", "缺陷日志：实时日志与历史日志，查看告警附件图片"),
        ("li", "系统设置：模型、推理参数、日志间隔、相机曝光/增益等"),
        ("h1", "3. 快速上手流程"),
        ("li", "进入『实时监控』→ 点击『刷新设备列表』发现相机"),
        ("li", "在 Slot 0~3 选择相机并连接"),
        ("li", "画面出现后：右上角『眼睛』切换检测框显示；『全屏』放大单路"),
        ("li", "选择检测模式：自动模式（持续推理）/ 手动模式（点『单次检测』触发）"),
        ("h1", "4. 检测与抓拍"),
        ("h2", "4.1 自动检测"),
        ("p", "自动模式下：系统持续推理；发现缺陷会写入日志并附带截图链接。"),
        ("h2", "4.2 手动检测"),
        ("p", "手动模式下：点击『单次检测』对当前已连接相机抓拍并推理，生成结果与图片链接。"),
        ("h2", "4.3 图片检测（调试/离线）"),
        ("p", "在『实时监控』页面上传图片进行检测，系统会保存原图/结果图到 history。"),
        ("h1", "5. 缺陷日志与历史图片"),
        ("li", "实时日志：运行中自动滚动显示连接/告警/异常等"),
        ("li", "历史日志：点击『刷新日志』拉取最近记录"),
        ("li", "查看缺陷图片：带附件的日志条目可点开查看；图片文件在 history 目录"),
        ("h1", "6. 系统设置（常用项）"),
        ("h2", "6.1 模型"),
        ("p", "默认 best.* 对应 yolo26s；也可选择 yolo26n.pt 等其他模型。"),
        ("h2", "6.2 推理参数"),
        ("li", "conf：置信度阈值（越高越严格，误报少但可能漏检）"),
        ("li", "imgsz：推理输入尺寸（越大越清晰但更慢）"),
        ("h2", "6.3 相机参数"),
        ("p", "可对每个 Slot 设置曝光、增益；保存后会应用到对应相机。"),
        ("h1", "7. 常见问题"),
        ("li", "全屏切换 loading 较久：属于高清流首帧到达延迟，建议先关闭检测框或用手动模式。"),
        ("li", "找不到图片/配置：优先检查安装目录旁 HK_Tauri_Data；或访问 /paths 查看实际位置。"),
        ("li", "流媒体错误：查看 backend.log，确认后端是否正常启动、相机是否已连接。"),
    ]

    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>行李缺陷检测系统 使用手册</dc:title>
  <dc:creator>HK_Tauri</dc:creator>
  <cp:lastModifiedBy>HK_Tauri</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
"""

    app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Office Word</Application>
</Properties>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", _document_xml(manual))
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app_xml)

    return out_path


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    out = repo_root / "docs" / "软件使用手册.docx"
    print(generate_docx(out))
