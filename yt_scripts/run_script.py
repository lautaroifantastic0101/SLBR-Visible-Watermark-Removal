


from moviepy.editor import ColorClip, VideoFileClip, CompositeVideoClip

def create_shorts_with_borders(content_source, output_path, duration=5):
    """
    content_source: 可以是视频路径，也可以是已加载的 Clip
    """
    # 1. 定义全局尺寸
    W, H = 1080, 1920
    border_h = 168
    content_h = H - (border_h * 2) # 中间可用高度为 1584
    
    # 2. 创建 1080x1920 的黑色背景底层
    # 如果 content_source 是视频，背景时长应与视频一致
    if isinstance(content_source, str):
        main_content = VideoFileClip(content_source)
    else:
        main_content = content_source
        
    bg_clip = ColorClip(size=(W, H), color=(0, 0, 0)).set_duration(main_content.duration)
    
    # 3. 处理中间内容
    # 自动缩放内容以适应 1080x1584 的区域，同时保持比例
    main_content = main_content.resize(width=W) 
    if main_content.h > content_h:
        main_content = main_content.resize(height=content_h)
        
    # 4. 叠加图层
    # 将内容放在背景的正中间，即 y=168 的位置
    final_video = CompositeVideoClip([
        bg_clip,
        main_content.set_position(("center", border_h))
    ])
    
    # 5. 导出
    final_video.write_videofile(output_path, fps=30, codec="libx264")

# 使用示例
# create_shorts_with_borders("input_video.mp4", "final_shorts.mp4")



create_shorts_with_borders('/Users/wushan/Downloads/splitline_sample_0326_2.mp4', 'output.mp4')

