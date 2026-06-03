from yt_scripts.download_utils import download_youtube_video
import os


if __name__  == "__main__":
    download_youtube_video(
        'https://www.youtube.com/watch?v=ei2Pc4xV1cQ',
        "Printing - Roblox Beginners Scripting Tutorial #2 (2025)",
        save_dir="D:\\download_youtube",
        proxy="http://127.0.0.1:7890",
    )

    a = '123123123 123123 ??123123'
    b = os.path.normpath(a)
    c = os.path.splitext(b)
    print(c[0])