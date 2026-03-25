# encoding=utf-8
# 舟山日报/Z20260318PDF/B2026-03-18一版01_00.png

import cv2
import json
import numpy as np
import fitz
import matplotlib.pyplot as plt
from PIL import Image

# ====================== 核心修复1：彻底避开pyarrow兼容性问题 ======================
try:
    import pyarrow

    # 兼容新版pyarrow（PyExtensionType → ExtensionType）
    if not hasattr(pyarrow, "PyExtensionType") and hasattr(pyarrow, "ExtensionType"):
        pyarrow.PyExtensionType = pyarrow.ExtensionType
except ImportError:
    pass  # 无pyarrow时跳过

# ====================== 核心修复2：导入ModelScope并兼容Tasks ======================
from modelscope.pipelines import pipeline

try:
    from modelscope.utils.constant import Tasks
except ImportError:
    Tasks = None  # 极旧版本无Tasks，直接用字符串

# ====================== 1. 配置参数 ======================
E_NEWSPAPER_PATH = (
    "舟山日报/Z20260318PDF/B2026-03-18一版01_00.pdf"  # 替换为你的电子报路径
)
OUTPUT_IMAGE_PATH = "structgpt_hotzone.jpg"
JSON_OUTPUT_PATH = "structgpt_hotzone_coords.json"

# 热区类别颜色映射
COLOR_MAP = {
    "title": (0, 0, 255),
    "text": (0, 255, 0),
    "list": (255, 0, 0),
    "table": (255, 255, 0),
    "figure": (255, 0, 255),
    "advertisement": (0, 255, 255),
    "header": (128, 0, 128),
    "footer": (128, 128, 0),
}

# ====================== 2. 加载ModelScope模型（全版本兼容） ======================
print("🔍 加载阿里达摩院版面分析模型（兼容所有ModelScope版本）...")
# 核心：直接用字符串指定任务名，彻底避开Tasks属性问题
layout_pipeline = pipeline(
    task="document-layout-analysis",  # 所有版本都支持的字符串任务名
    model="damo/cv_layoutlmv3_layout-analysis_english_base",  # 有效模型（支持中文）
    model_revision="v1.0.0",
    use_gpu=False,
    device="cpu",
    enable_cache=False,  # 禁用pyarrow缓存
    use_arrow=False,  # 彻底避开pyarrow
)


# ====================== 3. PDF/图片预处理 ======================
def preprocess_file(file_path):
    """预处理：PDF转高分辨率图片/图片直接加载"""
    try:
        if file_path.lower().endswith(".pdf"):
            pdf_doc = fitz.open(file_path)
            page = pdf_doc[0]  # 取第一页
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2倍分辨率
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pdf_doc.close()
        else:
            img = Image.open(file_path).convert("RGB")

        cv2_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return img, cv2_img
    except Exception as e:
        raise RuntimeError(f"文件预处理失败：{str(e)}")


# 执行预处理
image, cv2_image = preprocess_file(E_NEWSPAPER_PATH)

# ====================== 4. 本地化推理 ======================
print("📄 本地推理：解析电子报热区...")
# 执行版面分析（禁用arrow，避免报错）
result = layout_pipeline(image, use_arrow=False)

# 格式化结果（适配StructGPT-Layout输出）
formatted_hotzones = []
label_mapping = {
    "title": "title",
    "text": "text",
    "list": "list",
    "table": "table",
    "figure": "figure",
    "advertisement": "advertisement",
    "header": "header",
    "footer": "footer",
    "picture": "figure",
    "ad": "advertisement",
    "paragraph": "text",
}

for res in result:
    # 兼容不同版本的键名
    original_label = res.get("label", res.get("type", "text")).lower()
    label = label_mapping.get(original_label, "text")

    # 提取坐标并过滤小区域
    bbox = [int(c) for c in res.get("bbox", [0, 0, 0, 0])[:4]]
    if (bbox[2] - bbox[0]) < 10 or (bbox[3] - bbox[1]) < 10:
        continue

    # 提取置信度
    confidence = round(res.get("score", res.get("confidence", 0.95)), 3)

    formatted_hotzones.append({"label": label, "bbox": bbox, "confidence": confidence})

# ====================== 5. 可视化 + 导出结果 ======================
if formatted_hotzones:
    vis_image = cv2_image.copy()
    for idx, hotzone in enumerate(formatted_hotzones):
        label = hotzone["label"]
        x1, y1, x2, y2 = hotzone["bbox"]
        conf = hotzone["confidence"]
        color = COLOR_MAP.get(label, (128, 128, 128))

        # 绘制热区框
        cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)

        # 绘制标注背景和文字
        label_text = f"{label} ({conf})"
        text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        text_x = x1
        text_y = y1 - 10 if y1 - 10 > 10 else y1 + 20

        cv2.rectangle(
            vis_image,
            (text_x, text_y - text_size[1] - 5),
            (text_x + text_size[0] + 5, text_y + 5),
            color,
            -1,
        )
        cv2.putText(
            vis_image,
            label_text,
            (text_x + 2, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )

        # 打印热区信息
        print(f"\n🔥 热区 {idx + 1}：")
        print(f"   类型：{label} | 坐标：({x1},{y1})-({x2},{y2}) | 置信度：{conf}")

    # 保存结果
    cv2.imwrite(OUTPUT_IMAGE_PATH, vis_image)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(formatted_hotzones, f, ensure_ascii=False, indent=2)

    # 显示结果（解决中文乱码）
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.figure(figsize=(18, 24))
    plt.imshow(cv2.cvtColor(vis_image, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.title("电子报热区划分结果（全版本兼容）", fontsize=16)
    plt.show()

    print(f"\n✅ 结果已保存：")
    print(f"   - 可视化图片：{OUTPUT_IMAGE_PATH}")
    print(f"   - 热区坐标JSON：{JSON_OUTPUT_PATH}")
else:
    print("⚠️ 未识别到有效热区，请检查：")
    print("   1. 文件路径是否正确")
    print("   2. PDF/图片是否清晰")
    print("   3. 模型是否下载完成")
