# 【step 2】输入路径，对视频进行解析


cd D:\codes\video-analyzer\
.venv\Scripts\activate     


$files = Get-ChildItem -Path D:\download_youtube\0610_01\ -Filter "*.mp4"
foreach ($file in $files) {
    $source_path = $file.FullName
    $fn = [System.IO.Path]::GetFileName($source_path)
    $fn_prefix = [System.IO.Path]::GetFileNameWithoutExtension($source_path)
    Write-Output $fn
    Write-Output $source_path
    Write-Output $fn_prefix
    
    # video-analyzer --output  D:\download_youtube\  --device cuda --keep-frames "$source_path" --log-level INFO
    video-analyzer   --device cuda --keep-frames "$source_path" --log-level INFO

    # video-analyzer --device cuda --keep-frames "$source_path"  

    # 输出路径
    mkdir D:\\download_youtube\\output\\"$fn_prefix"

    # 代码运行结果移动
    Move-Item d:\codes\video-analyzer\output D:\\download_youtube\\output\\"$fn_prefix" 
}

# $source_path = "D:\\download_youtube\\Printing - Roblox Beginners Scripting Tutorial #2 .mp4"
