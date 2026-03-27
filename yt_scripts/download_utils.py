import requests
import os
import re

def download_douyin_video(video_url, title, save_dir="./"):
    """
    video_url: 视频的真实播放地址 (play_addr)
    title: 视频标题，将作为文件名
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 清洗文件名，去除特殊字符防止报错
    filename = re.sub(r'[\\/:*?"<>|]', '', title)[:50] + ".mp4"
    save_path = os.path.join(save_dir, filename)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    try:
        # stream=True 适合下载大文件，避免内存溢出
        with requests.get(video_url, headers=headers, stream=True, timeout=60) as r:
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