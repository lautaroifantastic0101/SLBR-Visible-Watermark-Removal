# 【step 2】输入路径，对视频进行解析


cd D:\codes\video-analyzer\
.venv\Scripts\activate     


$files = Get-ChildItem -Path D:\download_youtube\0612_02\ -Filter "*.mp4"

foreach ($file in $files) {
    $source_path = $file.FullName
    $fn = [System.IO.Path]::GetFileName($source_path)
    $fn_prefix = [System.IO.Path]::GetFileNameWithoutExtension($source_path)
    Write-Output $fn
    # Write-Output "视频路径：" + $source_path
    # Write-Output "视频前缀：" + $fn_prefix
    $clean_prefix = $fn_prefix -replace " ", "-"
    $dest_path = "D:\\ai_note_proj\\video_analysis_result\\" + $clean_prefix

    Write-Output $dest_path
    Remove-Item $dest_path -Recurse -Force -ErrorAction SilentlyContinue

    video-analyzer --device cuda --keep-frames "$source_path" --log-level INFO

    # 代码运行结果移动
    Move-Item d:\codes\video-analyzer\output $dest_path  

}
