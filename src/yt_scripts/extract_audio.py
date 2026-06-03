import os
import shutil
import subprocess

def build_audio_output_path(video_path, audio_ext=".mp3"):
    base_path, _ = os.path.splitext(video_path)
    return f"{base_path}{audio_ext}"


def extract_audio_from_video(video_path, output_audio_path=None):
    if output_audio_path is None:
        output_audio_path = build_audio_output_path(video_path)

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        print("音频提取失败: 未找到 ffmpeg，请先安装 ffmpeg 并加入 PATH。")
        return None

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "libmp3lame",
        output_audio_path,
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"音频提取成功，已保存至：{output_audio_path}")
        return output_audio_path
    except subprocess.CalledProcessError:
        print(f"音频提取失败: {video_path}")
        return None
    