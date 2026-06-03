import re

import glob
import os 

from yt_scripts.download_utils import download_youtube_video
from yt_scripts.extract_audio import extract_audio_from_video
from yt_scripts.audio_utils import transcribe_audio_to_file

output='D:\\download_video_samples'

urls = """
https://www.youtube.com/shorts/YIQuy-eNvn0||guess who rob the bank
"""



save_dir='D:\\download_video_samples'
safe_title = "CAN THE WORLD’S STRONGEST MAN BREAK REAL PRISON"
downloaded_files = sorted(glob.glob(os.path.join(save_dir, f"CAN THE WORLD’S STRONGEST MAN BREAK REAL PRISON_0.*")))
print(downloaded_files)



idx = 1
for line in urls.strip().split('\n'):
    print(line)
    url, title = line.strip().split('||')
    print(f"正在下载: {title} ({url})")
    # 下载save path


    safe_title = re.sub(r'[\\/:*?"<>|]', '', title).strip()[:50]
    safe_title_with_idx = f"{safe_title}_{idx}"
    
    save_path = download_youtube_video(url, safe_title_with_idx, output, proxy="http://127.0.0.1:7890")
    print('save_path', save_path)
    if save_path:
        audio_path = extract_audio_from_video(save_path)
        if audio_path:
            transcript_path = transcribe_audio_to_file(audio_path)
            print('transcript_path', transcript_path)

    
    
    idx += 1
