import json

from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, clips_array, vfx
import numpy as np
import easyocr
import cv2
import re
import time
import math
import os

import whisper









def overlay_text_area(video_path, output_path, boxes, mask_video_path):
    """
    增加：一个overlay mask
    boxes: OCR 返回的坐标列表 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    """
    video = VideoFileClip(video_path)

    print("video duration", video.duration)
    # 提取坐标的最大最小值形成矩形
    # box[0]是左上角，box[2]是右下角
    overlays = []
    for box in boxes:
        print(box)
        xmin, ymin = box[0]
        xmax, ymax = box[2]
        w, h = xmax - xmin, ymax - ymin
        print(xmin, ymin, w, h)
        # 使用视频短片作为mask
        target_w = w
        # 1. 加载并调整高度、时长(需要先调整时间长度)
        clip = VideoFileClip(mask_video_path).resize(height=int(h)).fx(vfx.loop, duration=video.duration)

        # 2. 计算重复次数
        # 假设目标宽度为 target_w
        repeat_count = math.ceil(target_w / clip.w)

        # 3. 横向拼接
        # clips_array 接收一个二维列表，[[clip, clip, clip]] 表示横向排列
        tiled_clip = clips_array([[clip] * (repeat_count+1)])

        # 4. 裁切掉超出 target_w 的部分
        # final_clip = tiled_clip.crop(x1=0, y1=0, x2=target_w, y2=int(h))

        # 5. 设置后续拼接的时候，在主视频的位置；以及设置开始的时间
        looped_clip_by_duration = tiled_clip\
        .set_start(0)\
        .set_position((int(xmin), int(ymin)))
        
        # 5. 使其在时间上循环，直到达到目标总长度
        # duration 参数指定了循环后的最终总长度
        # final_clip = final_clip.fx(vfx.loop, duration=video.duration).set_start(0).set_position((int(xmin), int(ymin)))
        overlays.append(looped_clip_by_duration)
    # 合成视频
    final_video = CompositeVideoClip([video] + overlays)
    final_video.write_videofile(output_path, codec="libx264")




def check_chinese_in_video(video_path, model_size="base"):
    """
    1. 提取视频音频
    2. 使用 Whisper 识别语音
    3. 利用正则匹配中文
    """
    audio_path = "temp_audio.wav"
    
    # --- 步骤 1: 提炼音频 ---
    print("正在提取音频...")
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, codec="pcm_s16le", logger=None)
    
    # --- 步骤 2: 语音识别 ---
    print(f"正在加载 Whisper 模型 ({model_size})...")
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    text = result["text"]
    
    # 清理临时文件
    video.close()
    os.remove(audio_path)
    
    # --- 步骤 3: 中文检测 ---
    # 匹配中文字符的正则表达式：[\u4e00-\u9fa5]
    has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', text))
    
    return {
        "has_chinese": has_chinese,
        "transcribed_text": text
    }




def is_chinese(text):
    """通过 Unicode 范围检查字符串中是否包含汉字"""
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def scan_video_for_chinese(video_path, sample_rate=1):
    """
    扫描视频是否存在中文字符
    :param sample_rate: 每秒扫描的帧数，默认1帧/秒
    """
    # 初始化 EasyOCR，指定语言为中文简体和英文
    reader = easyocr.Reader(['ch_sim', 'en'])

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f'fps: {fps}')

    interval = int(fps / sample_rate) if fps > 0 else 1

    frame_count = 0
    total_ocr_time = 0
    scan_count = 0
    print(f"开始扫描视频: {video_path}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % interval == 0:
            # 执行识别
            start_ocr = time.perf_counter()

            # 执行识别 (注意：如果你只需要检测是否存在，可以用 detail=0 提升一点速度)
            results = reader.readtext(frame)

            end_ocr = time.perf_counter()
            duration = end_ocr - start_ocr
            total_ocr_time += duration
            scan_count += 1
            print(f"帧 {frame_count} | 耗时: {duration:.4f}s | 结果: {results if results else '无文字'}")

            for text in results:
                print(text)
                if is_chinese(text[1]):
                    print(f"在 {frame_count/fps:.2f} 秒处发现中文: '{text[1]}'")
                    return True # 发现中文即可停止

        frame_count += 1

    cap.release()
    return False




# # 使用示例
# result = check_chinese_in_video("my_game_video.mp4")
# print(f"检测结果: {'包含中文' if result['has_chinese'] else '不包含中文'}")
# print(f"识别出的内容: {result['transcribed_text'][:100]}...")



# boxes = [[[np.int32(209), np.int32(285)], [np.int32(867), np.int32(285)], [np.int32(867), np.int32(345)], [np.int32(209), np.int32(345)]], [
#     [np.int32(310), np.int32(368)], [np.int32(782), np.int32(368)], [np.int32(782), np.int32(428)], [np.int32(310), np.int32(428)]]]  # 假设这是 OCR 拿到的坐标
# overlay_text_area("/content/test1708.mp4", "output6.mp4", boxes,
#                   "/Users/wushan/models/SLBR-Visible-Watermark-Removal/material/DancingBug.mp4")


def capture_video_screenshot(video_path, image_path, frame_time=None):
    """
    从视频中截取一张截图并保存为图片

    :param video_path: 视频文件路径
    :param image_path: 图片保存路径（包含文件名和扩展名，如 .jpg, .png）
    :param frame_time: 截取的时间点（秒），如果为None则截取第一帧
    :return: bool 成功返回True，失败返回False
    """
    try:
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"无法打开视频文件: {video_path}")
            return False

        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"视频信息: FPS={fps}, 总帧数={total_frames}")

        # 设置截取位置
        if frame_time is not None and fps > 0:
            # 根据时间设置帧位置
            frame_number = int(frame_time * fps)
            if frame_number >= total_frames:
                frame_number = total_frames - 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            print(f"设置到第 {frame_number} 帧 (时间: {frame_time}s)")
        else:
            # 截取第一帧
            print("截取第一帧")

        # 读取帧
        ret, frame = cap.read()
        if not ret:
            print("无法读取视频帧")
            cap.release()
            return False

        # 保存图片
        success = cv2.imwrite(image_path, frame)
        if success:
            print(f"截图已保存到: {image_path}")
        else:
            print(f"保存图片失败: {image_path}")

        # 释放资源
        cap.release()
        return success

    except Exception as e:
        print(f"截图过程中发生错误: {e}")
        return False



def create_shorts_with_borders(content_source, output_path, frame=None):
    """
    content_source: 可以是视频路径，也可以是已加载的 Clip
    output_path: 存储的视频文件
    frame: 资源素材的框架,
        [{"id":"df3cdd31-0a70-4502-b10f-a759f5cddf77","x":0.32589285714285715,"y":0.16331573928576226,
          "width":0.35044642857142855,"height":0.6687349745490686}]
    
    x,y,width,height 均为归一化坐标（0~1）相对于原视频
    作用：根据 frame 信息裁剪视频核心内容，输出一个 1080x1920 的短视频。
    """
    print('create_shorts_with_borders')
    # 1. 定义全局尺寸
    W, H = 1080, 1920
    border_h = 297.6
    content_h = H - (border_h * 2)  # 中间可用高度为 1584

    # 2. 读取视频
    if isinstance(content_source, str):
        main_content = VideoFileClip(content_source)
    else:
        main_content = content_source

    # 3. 根据 frame 信息裁剪
    print('frame')
    print(frame)
    frame = json.loads(frame)
    if frame and isinstance(frame, list) and len(frame) > 0:
        region = frame[0]
        print('region', region)
        if all(k in region for k in ("x", "y", "width", "height")):
            ow, oh = main_content.w, main_content.h
            x1 = max(0, region["x"] * ow)
            y1 = max(0, region["y"] * oh)
            x2 = min(ow, x1 + region["width"] * ow)
            y2 = min(oh, y1 + region["height"] * oh)

            if x2 > x1 and y2 > y1:
                # vfx.crop 的入参顺序是 x1, y1 (左上), x2, y2 (右下)
                print(f"裁剪区域: ({x1:.1f},{y1:.1f}) -> ({x2:.1f},{y2:.1f})")
                main_content = main_content.crop(x1=x1, y1=y1, x2=x2, y2=y2)
            else:
                print("frame 参数无效，跳过裁剪")
        else:
            print("frame 字段不完整，跳过裁剪")
    
    # main_content.write_videofile(output_path, fps=30, codec="libx264")

    # # 4. 创建背景
    bg_clip = ColorClip(size=(W, H), color=(0, 0, 0)).set_duration(main_content.duration)

    # # 5. 缩放主内容，保持比例
    main_content = main_content.resize(width=W)
    if main_content.h > content_h:
        main_content = main_content.resize(height=content_h)

    # # 6. 叠加到中间
    final_video = CompositeVideoClip([
        bg_clip,
        main_content.set_position(("center", border_h))
    ])

    # 7. 输出
    final_video.write_videofile(output_path, fps=30, codec="libx264")