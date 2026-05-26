from moviepy  import VideoFileClip

from yt_scripts.audio_utils import detect_chinese_segments, speechToText

def extract_audio_from_video(video_path, output_audio_path):
    # 1. 加载视频文件
    video = VideoFileClip(video_path)
    
    # 2. 提取音频并保存为目标格式（如 .mp3）
    video.audio.write_audiofile(output_audio_path)
    
    # 3. 关闭视频文件以释放资源
    video.close()
    print(f"音频提取成功，已保存至：{output_audio_path}")

# 使用示例
if __name__ == "__main__":
    # 请将 'input.mp4' 替换为你的视频文件实际路径
    # 请将 'output.mp3' 替换为你想要保存的音频文件名
    # extract_audio_from_video(r"D:\roblox视频素材\模仿对象\videoplayback_0509.mp4", "output.mp3")

    speechToText("D:\codes\SLBR-Visible-Watermark-Removal\output.mp3", model_size="base")
    