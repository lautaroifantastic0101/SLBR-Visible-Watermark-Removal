import re

import glob
import os 

from yt_scripts.download_utils import download_youtube_video
from yt_scripts.extract_audio import extract_audio_from_video
from yt_scripts.audio_utils import transcribe_audio_to_file





def main(urls, output):
    idx = 1
    for line in urls.strip().split('\n'):
        print(line)
        url, title = line.strip().split('||')
        print(f"正在下载: {title} ({url})")
        # 下载save path

        safe_title = re.sub(r'[\\/:*?"<>|]', '', title).strip()[:50]
        safe_title_with_idx = f"{idx}_{safe_title}"
        
        save_path = download_youtube_video(url, safe_title_with_idx, output, proxy="http://127.0.0.1:7890")
        print('save_path', save_path)
        if save_path:
            audio_path = extract_audio_from_video(save_path)
            if audio_path:
                transcript_path = transcribe_audio_to_file(audio_path)
                print('transcript_path', transcript_path)
        idx += 1


if __name__ == "__main__":
    ######################################################
    # 参数输入
    ######################################################
    output='D:\\download_video_samples_0606'
    os.makedirs(output, exist_ok=True)

    urls = """
    https://www.youtube.com/shorts/v0GXac3qMzc||WHO WON IN ROBLOX
    https://www.youtube.com/shorts/f3eZNMiGBCU||跳舞剧情
    https://www.youtube.com/shorts/PXEApbMLuHQ||泳池跳舞
    https://www.youtube.com/shorts/hrzKP3NkgAo||胶带绑人
    https://www.youtube.com/shorts/smSjJk5W4IM||甜甜圈被偷走
    https://www.youtube.com/shorts/Ugg1Cp7wn5Q||跳楼梯比赛
    https://www.youtube.com/shorts/qrdl9WF8t0g||帮助警察抓人
    """



    ######################################################
    # 运行程序
    ######################################################  
    main(urls, output)


