

from yt_scripts.download_utils import download_youtube_video

output='D:\\download_youtube'
fp = 'D:\\codes\\SLBR-Visible-Watermark-Removal\\config\\robloxstudio_learning.txt'

for line in open(fp, 'r', encoding='utf-8'):
    url, title = line.strip().split('||')
    print(f"正在下载: {title} ({url})")
    # 下载save path
    save_path = download_youtube_video(url, title, output, proxy="http://127.0.0.1:7890")

