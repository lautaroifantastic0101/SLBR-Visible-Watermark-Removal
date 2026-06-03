

import re

from yt_scripts.download_utils import download_youtube_video

output='D:\\download_youtube'
fp = 'D:\\codes\\SLBR-Visible-Watermark-Removal\\config\\ai_excel.txt'
idx = 1
for line in open(fp, 'r', encoding='utf-8'):
    url, title = line.strip().split('||')
    print(f"正在下载: {title} ({url})")
    # 下载save path
    
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title).strip()[:50]
    safe_title_with_idx = f"{safe_title}_{idx}"
    
    save_path = download_youtube_video(url, safe_title_with_idx, output, proxy="http://127.0.0.1:7890")
    
    idx += 1
