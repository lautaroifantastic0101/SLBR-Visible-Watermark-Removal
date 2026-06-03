import re
import whisper
import translators as ts
from pydub import AudioSegment
import time
import os
import subprocess
from scipy.io.wavfile import write as write_wav
import torch.serialization
torch.load = lambda *args, **kwargs: torch.serialization.load(*args, **kwargs)


def build_transcript_output_path(audio_path, output_ext=".txt"):
    base_path, _ = os.path.splitext(audio_path)
    return f"{base_path}{output_ext}"

def is_contains_chinese(text):
    """检查字符串中是否包含汉字"""
    return re.search(r'[\u4e00-\u9fff]', text) is not None


def speechToText(audio_path, model_size="base"):
    """将音频转录为文本

    Args:
        audio_path (_type_): _description_
        model_size (str, optional): _description_. Defaults to "base".

    Returns:
        _type_: _description_
    """
    # 1. 加载模型 (建议 Colab 选 base 或 small，兼顾速度与精度)
    model = whisper.load_model(model_size)
    
    # 2. 转录音频
    # 不指定 language 它可以自动检测，但在混合音频中，建议让它自由识别
    print(f"正在分析音频: {audio_path}...")
    result = model.transcribe(audio_path, verbose=False)

    print(result['text'])
    
    return result['text']


def transcribe_audio_to_file(audio_path, output_text_path=None, model_size="base", encoding="utf-8"):
    if output_text_path is None:
        output_text_path = build_transcript_output_path(audio_path)

    text = speechToText(audio_path, model_size=model_size)
    with open(output_text_path, "w", encoding=encoding) as file_obj:
        file_obj.write(text.strip())
        file_obj.write("\n")

    print(f"文本提取成功，已保存至：{output_text_path}")
    return output_text_path



def detect_chinese_segments(audio_path, model_size="base"):
    """识别语音是否存在中文，如果有的话，返回list

    Args:
        audio_path (_type_): _description_
        model_size (str, optional): _description_. Defaults to "base".

    Returns:
        _type_: _description_
    """
    # 1. 加载模型 (建议 Colab 选 base 或 small，兼顾速度与精度)
    model = whisper.load_model(model_size)
    
    # 2. 转录音频
    # 不指定 language 它可以自动检测，但在混合音频中，建议让它自由识别
    print(f"正在分析音频: {audio_path}...")
    result = model.transcribe(audio_path, verbose=False)

    print(result['segments'])
    
    chinese_segments = []
    
    # 3. 遍历所有片段
    for segment in result['segments']:
        text = segment['text']
        start = segment['start']
        end = segment['end']
        
        # 4. 判断该片段是否包含中文
        if is_contains_chinese(text):
            chinese_segments.append({
                "start": start,
                "end": end,
                "text": text.strip()
            })
            print(f"[{start:6.2f}s -> {end:6.2f}s]: {text.strip()}")

    return chinese_segments



# 1. 翻译模块 (中文 -> 英文)
def translate_text(text, from_lang='zh', to_lang='en'):
    """将中文翻译给英文

    Args:
        text (_type_): _description_
        from_lang (str, optional): _description_. Defaults to 'zh'.
        to_lang (str, optional): _description_. Defaults to 'en'.

    Returns:
        _type_: _description_
    """
    try:
        translated = ts.translate_text(text, from_lang=from_lang, to_lang=to_lang, translator='google')
        print(f"Original: {text} -> Translated: {translated}")
        return translated
    except Exception as e:
        print(f"Translation Error: {e}")
        return None


def generate_raw_speech(text, output_path="raw_speech.wav"):
    """将英文生成音频文件

    Args:
        text (_type_): _description_
        output_path (str, optional): _description_. Defaults to "raw_speech.wav".

    Returns:
        _type_: _description_
    """
    # 2. TTS 生成模块 (Bark)
    # 在 Colab 中，Bark 需要下载模型，通常在第一次运行。
    # 这里我们使用简化的伪代码表示其核心调用逻辑。
    print(f"Generating raw speech for: '{text}'...")
    
    # --- Bark 核心调用 (需要事先安装依赖) ---
    from bark import SAMPLE_RATE, generate_audio, preload_models
    preload_models()
    audio_array = generate_audio(text, history_prompt="v2/en_speaker_6")
    write_wav(output_path, SAMPLE_RATE, audio_array)
    # ----------------------------------------
    
    # 模拟生成一个 5 秒的音频文件用于测试
    # 在实际项目中，必须使用真正的 TTS 引擎。
    # silence = AudioSegment.silent(duration=5000) # 5 seconds
    # silence.export(output_path, format="wav")

    print(f"Raw speech generated: {output_path}")
    return output_path


def adjust_audio_duration(input_path, output_path, target_duration):
    """
    使用 FFmpeg 调整音频时长。
    target_duration: 目标时长（秒）
    """
    # 3. 核心变速模块 (FFmpeg)
    # 获取原始音频时长
    audio = AudioSegment.from_file(input_path)
    original_duration = len(audio) / 1000.0  # 秒
    print(f"Original duration: {original_duration:.2f}s, Target: {target_duration:.2f}s")
    
    if original_duration == 0:
        return None
    
    # 计算变速比率 (speed ratio = target / original)
    # ratio > 1: 加速， ratio < 1: 减速
    ratio = original_duration / target_duration
    print(f"Calculated Speed Ratio: {ratio:.4f}")
    
    # 使用 FFmpeg 的 atempo 过滤器进行变速
    # atempo 过滤器可以只改变语速而不改变音调，支持范围通常在 0.5 - 2.0 之间。
    # 如果超出此范围，画面会听起来很不自然。
    cmd = [
        'ffmpeg',
        '-y',               # 覆盖输出文件
        '-i', input_path,  # 输入文件
        '-filter:a', f'atempo={ratio:.4f}', # 变速过滤器
        '-vn',              # 禁用视频
        output_path         # 输出文件
    ]
    
    # 执行命令
    subprocess.run(cmd, check=True)
    print(f"✅ Final audio adjusted to {target_duration}s: {output_path}")
    return output_path