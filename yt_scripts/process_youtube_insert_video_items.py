import argparse
import json
import os
import re
import datetime
from cloudflare import Cloudflare





def insert_video_tb(filename, client, database_id, account_id):
        # 读取 JSONL 文件

    with open(filename, 'r', encoding='utf-8') as f:

        for line in f:
            if line.strip():
                data = json.loads(line.strip())
                # 映射字段
                keyword = data.get('keyword')
                crawl_pt = data.get('crawl_pt', 'default')
                title = data.get('title')
                link = data.get('link')
                channel = data.get('channel')
                channel_url = data.get('channel_url')
                views_raw = data.get('views_raw')
                views_value = data.get('views_value')
                publish_date_raw = data.get('publish_date_raw')
                publish_date_clean = data.get('publish_date_clean')

                # 构造 SQL
                sql = """
                INSERT OR IGNORE INTO youtube_video_crawl_item_tb 
                (keyword, crawl_pt, title, link, channel, channel_url, views_raw, views_value, publish_date_raw, publish_date_clean)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = [keyword, crawl_pt, title, link, channel, channel_url, views_raw, views_value, publish_date_raw, publish_date_clean]

                resp = client.d1.database.query(
                    database_id=database_id,
                    account_id=account_id,
                    sql=sql,
                    params=params)


def extract_date_from_filename(filename: str) -> str | None:
    """从文件名中提取 8 位日期 (YYYYMMDD)，并返回格式化为 YYYY-MM-DD 的字符串。

    示例: 'kw_cf_game_result_20260318' -> '2026-03-18'
    如果未找到或日期不合法，返回 None。
    """
    if not filename:
        return None

    # 只取文件名部分（去掉路径）
    base = os.path.basename(filename)

    # 查找连续的 8 位数字
    m = re.search(r"(\d{8})", base)
    if not m:
        return None

    s = m.group(1)
    try:
        year = int(s[0:4])
        month = int(s[4:6])
        day = int(s[6:8])
        # 验证日期合法性
        dt = datetime.date(year, month, day)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description="将爬虫文件塞入到数据库中")
    parser.add_argument("--cf_d1_api_token", required=False, help="Cloudflare D1 API Token，可通过环境变量 CF_D1_API_TOKEN 传递")
    parser.add_argument("--cf_ai_api_token", required=False, help="Cloudflare AI API Token，可通过环境变量 CF_D1_API_TOKEN 传递")
    parser.add_argument("--cf_d1_account_id", required=False, help="Cloudflare D1 ACCOUNT_ID，可通过环境变量 CF_D1_ACCOUNT_ID 传递")
    parser.add_argument("--cf_d1_database_id", required=False, help="Cloudflare D1 DATABASE_ID，可通过环境变量 CF_D1_DATABASE_ID 传递")
    parser.add_argument("--input_file", required=True, help="输入文件路径")

    args = parser.parse_args()

    # 获取参数
    api_token = args.cf_d1_api_token or os.getenv('CF_D1_API_TOKEN')
    account_id = args.cf_d1_account_id or os.getenv('CF_D1_ACCOUNT_ID')
    database_id = args.cf_d1_database_id or os.getenv('CF_D1_DATABASE_ID')

    client = Cloudflare(api_token=api_token)
    insert_video_tb(args.input_file, client, database_id, account_id)


if __name__ == "__main__":
    main()