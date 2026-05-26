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


def download_files(client, bucketname, remote_folder, local_folder):
    """
    从 R2 下载指定文件夹到本地

    Args:
        client: boto3 S3 客户端
        bucketname: R2 桶名
        remote_folder: R2 中的文件夹路径（前缀）
        local_folder: 本地文件夹路径
    """
    try:
        # 确保本地文件夹存在
        os.makedirs(local_folder, exist_ok=True)

        # 列出 R2 中指定前缀的所有对象
        paginator = client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucketname, Prefix=remote_folder)

        downloaded_count = 0
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # 计算相对路径
                    relative_path = key[len(remote_folder):].lstrip('/')
                    if not relative_path:
                        continue  # 跳过文件夹本身

                    local_file_path = os.path.join(local_folder, relative_path)

                    # 确保本地子文件夹存在
                    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                    # 下载文件
                    print(f"Downloading {key} to {local_file_path}")
                    client.download_file(bucketname, key, local_file_path)
                    downloaded_count += 1

        print(f"Downloaded {downloaded_count} files from {remote_folder} to {local_folder}")
        return True

    except Exception as e:
        print(f"Error downloading files: {e}")
        return False



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
        print(f"Error uploading file {local_file_path}: {e}")


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
            # print(f"更新成功！受影响行数: {meta.rows_written}")
        else:
            print(f"更新失败 id{id}: {response.result[0].errors}")
            
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
            # 参数化查询，防止注入，并更新 updated_at 字段为当前时间
            sql="UPDATE tro_post_img SET new_url = ?, img_type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params=[url, class_name, target_id]
        )
        # 检查是否更新成功
        if response.result[0].success:
            meta = response.result[0].meta
            # print(f"更新成功！受影响行数: {meta.rows_written}")
        else:
            print(f"更新失败: {response.result[0].errors}")
    except Exception as e:
        print(f"执行出错: {e}")

# 调用例子

def get_origin_urls_with_null_new_url(client, ACCOUNT_ID, DATABASE_ID, limit=100000, start_pt='2001-01-01', end_pt='2099-01-01', origin_post_id=None):
    """
    查询 tro_post_img 表中 new_url 为 null 的 origin_url 列表

    Args:
        client: Cloudflare D1 客户端
        ACCOUNT_ID: D1 account id
        DATABASE_ID: D1 database id

    Returns:
        List[str]: origin_url 列表
    """
    if origin_post_id is not None:
        sql = f"""
                SELECT id, origin_url FROM tro_post_img 
                WHERE new_url IS NULL 
                and source_type in  ( 'CifTRONewsItem', 'MaijiaxingiquTRONewsItem', 'QqdipTROItem', 'RuiguanTROItem')
                and origin_post_id = '{origin_post_id}'
                LIMIT {limit}
                """
    else:
        sql = f"""
                SELECT id, origin_url FROM tro_post_img 
                WHERE new_url IS NULL 
                and source_type in  ( 'CifTRONewsItem', 'MaijiaxingiquTRONewsItem', 'QqdipTROItem', 'RuiguanTROItem')
                and created_at between '{start_pt}' and '{end_pt}'
                LIMIT {limit}
                """
    print(sql)
    try:
        response = client.d1.database.query(
            account_id=ACCOUNT_ID,
            database_id=DATABASE_ID,
            sql=sql
        )
        # 处理返回结果，假定 response.result[0].results 为结果集
        records = response.result[0].results if hasattr(response.result[0], "results") else []
        # 返回 [(id, origin_url), ...]
        result = [(row["id"], row["origin_url"]) for row in records if "origin_url" in row and "id" in row]
        # INSERT_YOUR_CODE
        print("DEBUG: get_origin_urls_with_null_new_url result size =", len(result))
        return result
    except Exception as e:
        print(f"执行查询出错: {e}")
        return []





if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="下载 R2 文件夹到本地")
    parser.add_argument("--remote_folder", required=True, help="R2 中的远程文件夹路径")
    parser.add_argument("--local_folder", required=True, help="本地文件夹路径")

    args = parser.parse_args()

    ACCOUNT_ID = os.getenv("CF_D1_ACCOUNT_ID")
    ACCESS_KEY_ID = os.getenv("CF_R2_ACCESS_KEY_ID")
    SECRET_ACCESS_KEY = os.getenv("CF_R2_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("CF_R2_BUCKET_NAME")

    ENDPOINT_URL = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

    s3_client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY,
    )

    print("======client 初始化完成")

    # 下载 R2 文件夹到本地
    download_files(s3_client, bucket_name, args.remote_folder, args.local_folder)
            