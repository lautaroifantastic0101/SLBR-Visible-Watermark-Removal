from cloudflare import Cloudflare
import os

from dotenv import load_dotenv

load_dotenv()



token = os.getenv("CF_D1_API_TOKEN")
account_id = os.getenv("CF_D1_ACCOUNT_ID")
database_id = os.getenv("CF_D1_DATABASE_ID")



client = Cloudflare(
    api_token=token,  # This is the default and can be omitted
)





if __name__ == '__main__':
    # INSERT_YOUR_CODE
    import argparse

    parser = argparse.ArgumentParser(description="Script to process Cloudflare D1 database and images.")
    parser.add_argument('--image_dir', type=str, required=True, help="图片存储路径")
    args = parser.parse_args()
    
    image_dir = args.image_dir
    # PROXY_URL = "http://127.0.0.1:7890"  # 替换成您的代理地址
    # os.environ['HTTP_PROXY'] = PROXY_URL
    # os.environ['HTTPS_PROXY'] = PROXY_URL
    # 执行查询
    try:
        page = client.d1.database.query(
            database_id=database_id,
            account_id=account_id,
            sql="select * from tro_post_img where new_url is null limit ?",
            params=["10"]  # 使用参数化查询防止 SQL 注入
        )
        # result = page[0]
        url_list = []
        for row in page.result[0].results:
            print(row['origin_url'])
            url_list.append(row['origin_url'])

            
        # INSERT_YOUR_CODE
        import requests

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        for idx, url in enumerate(url_list):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                # 尝试从url提取文件名，否则使用索引
                filename = os.path.basename(url.split("?")[0]) or f"{idx}.jpg"
                file_path = os.path.join(image_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"已下载: {url} -> {file_path}")
                import time
                import random
                delay = 1 + random.uniform(0, 1)
                time.sleep(delay)
            except Exception as e:
                print(f"下载失败 {url}: {e}")



        # for row in result.results:
        #     print(row['origin_url'])


        # 打印结果
        # for row in page.result:
            # print(row['id'])
    except Exception as e:
        print(f"查询失败: {e}")