import glob
import importlib
import os
import re

import requests


def _resolve_proxy(proxy=None):
    if proxy:
        return proxy

    return (
        os.getenv("HTTPS_PROXY")
        or os.getenv("https_proxy")
        or os.getenv("HTTP_PROXY")
        or os.getenv("http_proxy")
        or os.getenv("ALL_PROXY")
        or os.getenv("all_proxy")
    )


def _build_requests_proxies(proxy=None):
    proxy_url = _resolve_proxy(proxy)
    if not proxy_url:
        return None

    return {
        "http": proxy_url,
        "https": proxy_url,
    }

def download_douyin_video(video_url, title, save_dir="./", proxy=None):
    """
    video_url: 视频的真实播放地址 (play_addr)
    title: 视频标题，将作为文件名
    proxy: 可选代理地址，例如 http://127.0.0.1:7890
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 清洗文件名，去除特殊字符防止报错
    filename = re.sub(r'[\\/:*?"<>|]', '', title)[:50] + ".mp4"
    save_path = os.path.join(save_dir, filename)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    proxies = _build_requests_proxies(proxy)

    try:
        # stream=True 适合下载大文件，避免内存溢出
        with requests.get(video_url, headers=headers, stream=True, timeout=60, proxies=proxies) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"下载成功: {filename}")
        return save_path
        # return True
    except Exception as e:
        print(f"下载失败 {title}: {e}")
        return None
        # return False


def download_youtube_video(video_url, title, save_dir="./", proxy=None):
    """
    video_url: 视频的真实播放地址
    title: 视频标题，将作为文件名
    proxy: 可选代理地址，例如 http://127.0.0.1:7890
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    safe_title = re.sub(r'[\\/:*?"<>|]', '', title).strip()[:50]
    if not safe_title:
        safe_title = "youtube_video"

    output_template = os.path.join(save_dir, f"{safe_title}.%(ext)s")

    try:
        YoutubeDL = importlib.import_module("yt_dlp").YoutubeDL
    except ImportError:
        print("下载 YouTube 视频失败: 缺少依赖 yt-dlp，请先安装 requirements.txt 中的依赖。")
        return None

    ydl_opts = {
        "outtmpl": output_template,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    proxy_url = _resolve_proxy(proxy)
    if proxy_url:
        ydl_opts["proxy"] = proxy_url

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        downloaded_files = sorted(glob.glob(os.path.join(save_dir, f"{safe_title}.*")))
        if not downloaded_files:
            print(f"下载失败 {title}: 未找到下载后的文件")
            return None

        preferred_path = None
        for path in downloaded_files:
            if path.lower().endswith(".mp4"):
                preferred_path = path
                break

        save_path = preferred_path or downloaded_files[-1]
        print(f"下载成功: {os.path.basename(save_path)}")
        return save_path
    except Exception as e:
        video_id = info.get("id") if isinstance(locals().get("info"), dict) else None
        if video_id:
            partial_files = glob.glob(os.path.join(save_dir, f"*{video_id}*"))
            for partial_file in partial_files:
                if os.path.isfile(partial_file):
                    try:
                        os.remove(partial_file)
                    except OSError:
                        pass

        print(f"下载失败 {title}: {e}")
        return None
 

