from mmap import ACCESS_COPY
import os
import shutil
from turtle import up, update
import zipfile
from pathlib import Path
import boto3
from cloudflare import Cloudflare
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()




def upload_file(client, bucketname, local_file_path, upload_r2_key):
    """上传文件到r2数据库中
    Args:
        client (_type_): _description_
        bucketname (_type_): _description_
        local_file_path (_type_): _description_
        upload_r2_key (_type_): _description_
    """
    object_key = upload_r2_key
    try:
        client.upload_file(
            Filename=local_file_path,
            Bucket=bucketname,
            Key=object_key,
            ExtraArgs={
                'ContentType': f'image/{upload_r2_key.split(".")[-1]}'  # 简单的 MIME 类型推断
            }
        )
        print(f"File {upload_r2_key} uploaded to bucket '{bucketname}'.")
    except Exception as e:
        print(f"Error uploading file: {e}")


def update_image_url(client, target_id, url, ACCOUNT_ID, DATABASE_ID):
    try:
        response = client.d1.database.query(
            account_id=ACCOUNT_ID,
            database_id=DATABASE_ID,
            # 使用参数化查询防止 SQL 注入
            sql="UPDATE tro_post_img SET new_url = ? WHERE id = ?",
            params=[url, target_id]
        )
        
        # 检查是否更新成功
        if response.result[0].success:
            meta = response.result[0].meta
            print(f"更新成功！受影响行数: {meta.rows_written}")
        else:
            print(f"更新失败: {response.result[0].errors}")
            
    except Exception as e:
        print(f"执行出错: {e}")


def update_image_url_and_class(client, target_id, url, class_name, ACCOUNT_ID, DATABASE_ID):
    """更新 tro_post_img 表的 new_url 和 class_name 字段
    Args:
        client: Cloudflare D1 客户端
        target_id: 要更新的记录 id
        url: 新的图片 url
        class_name: 分类名
        ACCOUNT_ID: D1 account id
        DATABASE_ID: D1 database id
    """
    try:
        response = client.d1.database.query(
            account_id=ACCOUNT_ID,
            database_id=DATABASE_ID,
            # 参数化查询，防止注入
            sql="UPDATE tro_post_img SET new_url = ?, img_type = ? WHERE id = ?",
            params=[url, class_name, target_id]
        )
        # 检查是否更新成功
        if response.result[0].success:
            meta = response.result[0].meta
            print(f"更新成功！受影响行数: {meta.rows_written}")
        else:
            print(f"更新失败: {response.result[0].errors}")
    except Exception as e:
        print(f"执行出错: {e}")

# 调用例子




if __name__ == "__main__":
    zip_path = '/Users/wushan/Downloads/rst_20260120121511_1801_2111.zip'
    output_dir = '/Users/wushan/Downloads/tmp'
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    ACCOUNT_ID = os.getenv("CF_D1_ACCOUNT_ID")
    ACCESS_KEY_ID = os.getenv("CF_R2_ACCESS_KEY_ID")
    SECRET_ACCESS_KEY = os.getenv("CF_R2_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("CF_R2_BUCKET_NAME")

    d1_token = os.getenv("CF_D1_API_TOKEN")
    d1_database_id = os.getenv("CF_D1_DATABASE_ID")

    

    ENDPOINT_URL = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

    s3_client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY,
    )
    d1_client = Cloudflare(
        api_token=d1_token,  # This is the default and can be omitted
    )

    print("======client 初始化完成")


    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(output_dir)
        print(f"已解压到 {output_dir}")

    # 定义目录路径
    out_put_dir = Path(output_dir)

    # 定义图片后缀名集合（使用集合提高查找速度）
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}

    # rglob('*') 表示递归遍历所有子文件夹；如果只想看当前层级，改用 glob('*')
    for img_path in out_put_dir.rglob('*'):
        # 检查文件后缀是否在图片后缀集合中
        print('img_path', img_path)
        if img_path.suffix.lower() in image_extensions:
            now = datetime.now()
            date_path = f"/{now.year}/{now.month:02d}/{now.day:02d}"
            # print(date_path)
            
            import hashlib
            md5_hash = hashlib.md5(img_path.name.encode('utf-8')).hexdigest()
            # print(f"MD5（32位）: {md5_hash}")

            extension = img_path.suffix.lower()  # 包括点，如 ".jpg"
            # print(f"后缀名: {extension}")
            
            row_id = img_path.name.split('_')[0]
            upload_r2_key = f'{date_path}/{md5_hash}{extension}'
            print(upload_r2_key)
            # print(f"文件名: {img_path.name}")
            # print(f"完整路径: {img_path}")

            
            # ------------------------------------------------------
            # 上传文件 到r2 存储中
            # 上传成功以后，将key更新到d1 数据库对应的行中
            # ------------------------------------------------------
            try:
                upload_file(client=s3_client, bucketname=bucket_name, local_file_path=img_path, upload_r2_key=upload_r2_key)
                update_image_url(d1_client, row_id, upload_r2_key, ACCOUNT_ID, d1_database_id)
                
            except Exception as e:
                continue
            