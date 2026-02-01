"""
流水线：从 CSV（id, url）下载图片 -> YOLO 分类 -> SLBR 去水印 -> 保存到输出目录。

使用示例（在项目根目录执行）:
  python -m src.runs.tro_img_reco \\
    --csv /path/to/images.csv \\
    --download_dir /path/to/download \\
    --processed_dir /path/to/processed \\
    --slbr_model /path/to/model_best.pth.tar \\
    --yolo_model /path/to/yolov8n-cls.pt

CSV 格式：表头需含 id 和 url 列（大小写不敏感）。
"""
import argparse
import os
import sys
import csv
import requests
import torch
import torch.nn.functional as F
import cv2
import numpy as np

# 项目根目录加入 path
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import src.networks as nets
import src.models as models
from options import Options


def tensor2np(x, isMask=False):
    if isMask:
        if x.shape[1] == 1:
            x = x.repeat(1, 3, 1, 1)
        x = ((x.cpu().detach())) * 255
    else:
        x = x.cpu().detach()
        mean = 0
        std = 1
        x = (x * std + mean) * 255
    return x.numpy().transpose(0, 2, 3, 1).astype(np.uint8)


def preprocess(file_path, img_size=512):
    img_J = cv2.imread(file_path)
    if img_J is None:
        return None
    img_J = cv2.cvtColor(img_J, cv2.COLOR_BGR2RGB).astype(np.float16) / 255.0
    img_J = torch.from_numpy(img_J.transpose(2, 0, 1)[np.newaxis, ...])
    img_J = F.interpolate(img_J.float(), size=(img_size, img_size), mode="bilinear")
    return img_J


def download_images_from_csv(csv_path: str, download_dir: str) -> list:
    """从 CSV（id, url）下载图片到 download_dir，返回本地路径列表 [(id, local_path), ...]。"""
    os.makedirs(download_dir, exist_ok=True)
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV 无表头，需要 id 和 url 列")
        names = [c.strip() for c in reader.fieldnames]
        names_lower = [c.lower() for c in names]
        id_idx = names_lower.index("id") if "id" in names_lower else 0
        url_idx = names_lower.index("url") if "url" in names_lower else (1 if len(names) > 1 else 0)
        id_col, url_col = names[id_idx], names[url_idx]
        for row in reader:
            raw = dict(row)
            pid = raw.get(id_col) or raw.get("id") or raw.get("ID")
            url = raw.get(url_col) or raw.get("url") or raw.get("URL")
            if not url or not pid:
                continue
            rows.append((str(pid).strip(), url.strip()))
    results = []
    for pid, url in rows:
        ext = ".jpg"
        if "." in url.split("?")[0]:
            ext = "." + url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        local_name = f"{pid}{ext}"
        local_path = os.path.join(download_dir, local_name)
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with open(local_path, "wb") as fp:
                fp.write(r.content)
            results.append((pid, local_path))
        except Exception as e:
            print(f"下载失败 [{pid}] {url}: {e}")
    return results


def load_slbr_model(model_path: str):
    """加载 SLBR 去水印模型。"""
    parser = Options().init(argparse.ArgumentParser())
    args = parser.parse_args([])
    args.resume = model_path
    args.evaluate = True
    args.nets = "slbr"
    args.models = "slbr"
    args.crop_size = 512
    args.input_size = 512
    args.gan_norm = getattr(args, "gan_norm", False)
    Machine = models.__dict__[args.models](datasets=(None, None), args=args)
    Machine.model.eval()
    return Machine, args, Machine.device


def classify_with_yolo(image_path: str, yolo_model_path: str):
    """使用 YOLO 对单张图片分类，返回预测结果（类别等）。"""
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        print("未安装 ultralytics，跳过分类步骤。请: pip install ultralytics")
        return None
    model = YOLO(yolo_model_path)
    results = model.predict(source=image_path, verbose=False)
    if not results:
        return None
    r = results[0]
    if hasattr(r, "probs") and r.probs is not None:
        probs = r.probs
        top1 = getattr(probs, "top1", None)
        top1_conf = getattr(probs, "top1conf", 0.0)
        if top1 is None and hasattr(probs, "data"):
            top1 = probs.data.argmax().item()
            top1_conf = probs.data.max().item()
        top1 = 0 if top1 is None else int(top1)
        names = getattr(r, "names", None) or {}
        return {"class_id": top1, "class_name": names.get(top1, ""), "conf": float(top1_conf)}
    return None


def remove_watermark_slbr(Machine, args, device, image_path: str, crop_size: int = 512):
    """对单张图片做 SLBR 去水印，返回 BGR  numpy 图 (H,W,3)。"""
    img_t = preprocess(image_path, img_size=crop_size)
    if img_t is None:
        return None
    img_t = img_t.to(device).float()
    with torch.no_grad():
        if getattr(args, "gan_norm", False):
            inputs = img_t * 2.0 - 1.0
        else:
            inputs = img_t
        outputs = Machine.model(inputs)
    imoutput, immask_all, _ = outputs
    imoutput = imoutput[0]
    immask = immask_all[0]
    if getattr(args, "gan_norm", False):
        imfinal = imoutput * immask + (inputs) * (1 - immask)
        imfinal = (imfinal + 1.0) / 2.0
    else:
        imfinal = imoutput * immask + img_t * (1 - immask)
    out_rgb = tensor2np(imfinal)[0]
    return cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)


def main():
    parser = argparse.ArgumentParser(description="CSV 图片下载 -> YOLO 分类 -> SLBR 去水印")
    parser.add_argument("--csv", required=True, help="CSV 文件路径，表头含 id 和 图片 url")
    parser.add_argument("--download_dir", required=True, help="下载图片保存目录")
    parser.add_argument("--processed_dir", required=True, help="去水印后图片保存目录")
    parser.add_argument("--slbr_model", required=True, help="去水印 PyTorch 模型路径（如 model_best.pth.tar）")
    parser.add_argument("--yolo_model", required=True, help="YOLO 图片分类模型路径（如 yolov8n-cls.pt）")
    parser.add_argument("--skip_download", action="store_true", help="已下载则跳过下载步骤")
    args_cli = parser.parse_args()

    csv_path = os.path.abspath(args_cli.csv)
    download_dir = os.path.abspath(args_cli.download_dir)
    processed_dir = os.path.abspath(args_cli.processed_dir)
    slbr_model_path = os.path.abspath(args_cli.slbr_model)
    yolo_model_path = os.path.abspath(args_cli.yolo_model)

    if not os.path.isfile(csv_path):
        print(f"CSV 不存在: {csv_path}")
        return
    if not os.path.isfile(slbr_model_path):
        print(f"SLBR 模型不存在: {slbr_model_path}")
        return
    if not os.path.isfile(yolo_model_path):
        print(f"YOLO 模型不存在: {yolo_model_path}")
        return

    # 1) 下载
    if not args_cli.skip_download:
        id_paths = download_images_from_csv(csv_path, download_dir)
        print(f"下载完成，共 {len(id_paths)} 张")
    else:
        id_paths = []
        if os.path.isdir(download_dir):
            for f in os.listdir(download_dir):
                if f.startswith("."):
                    continue
                lower = f.lower()
                if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    pid = os.path.splitext(f)[0]
                    id_paths.append((pid, os.path.join(download_dir, f)))
        print(f"跳过下载，使用已有图片共 {len(id_paths)} 张")

    if not id_paths:
        print("没有可处理图片")
        return

    # os.makedirs(processed_dir, exist_ok=True)
    # Machine, slbr_args, device = load_slbr_model(slbr_model_path)
    # crop_size = getattr(slbr_args, "crop_size", 512)

    # for pid, local_path in id_paths:
    #     if not os.path.isfile(local_path):
    #         print(f"文件不存在，跳过: {local_path}")
    #         continue
    #     # 2) YOLO 分类
    #     cls_info = classify_with_yolo(local_path, yolo_model_path)
    #     if cls_info:
    #         print(f"[{pid}] 分类: {cls_info.get('class_name', '')} ({cls_info.get('conf', 0):.2f})")
    #     # 3) 去水印
    #     out_img = remove_watermark_slbr(Machine, slbr_args, device, local_path, crop_size)
    #     if out_img is None:
    #         print(f"[{pid}] 去水印失败（可能无法读取图片）")
    #         continue
    #     base, ext = os.path.splitext(os.path.basename(local_path))
    #     out_name = f"{base}{ext}" if ext else f"{base}.jpg"
    #     out_path = os.path.join(processed_dir, out_name)
    #     cv2.imwrite(out_path, out_img)
    #     print(f"[{pid}] 已保存: {out_path}")

    # print("全部完成。")


if __name__ == "__main__":
    main()
