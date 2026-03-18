import argparse
import json
import os
import re
import datetime
from cloudflare import Cloudflare
from dateutil.relativedelta import relativedelta




def insert_video_tb(filename, client, database_id, account_id):
        # 读取 JSONL 文件

    rank_index = 0
    with open(filename, 'r', encoding='utf-8') as f:
        crawl_pt = extract_date_from_filename(filename)

        for line in f:
            rank_index += 1
            if line.strip():
                data = json.loads(line.strip())
                # 映射字段
                keyword = data.get('keyword')
                crawl_pt =  crawl_pt
                title = data.get('title')
                link = data.get('link')
                channel = data.get('channel')
                channel_url = data.get('channel_url')
                views_raw = data.get('views_raw')
                views_value = data.get('views_value')
                publish_date_raw = data.get('publish_date_raw')
                publish_date_clean = parse_youtube_date(data.get('publish_date_clean'))

                # 构造 SQL
                sql = """
                INSERT INTO youtube_video_crawl_item_tb 
                (keyword, crawl_pt, title, link, channel, channel_url, views_raw, views_value, publish_date_raw, publish_date_clean, rank_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(keyword, crawl_pt, rank_index, link) DO UPDATE SET
                    title = excluded.title,
                    link = excluded.link,
                    channel = excluded.channel,
                    channel_url = excluded.channel_url,
                    views_raw = excluded.views_raw,
                    views_value = excluded.views_value,
                    publish_date_raw = excluded.publish_date_raw,
                    publish_date_clean = excluded.publish_date_clean,
                    rank_index = excluded.rank_index,
                    updated_at = CURRENT_TIMESTAMP
                """
                params = [keyword, crawl_pt, title, link, channel, channel_url, views_raw, views_value, publish_date_raw, publish_date_clean, rank_index]
                # print(f"debug {sql}")


                resp = client.d1.database.query(
                    database_id=database_id,
                    account_id=account_id,
                    sql=sql,
                    params=params)

                # 统一的错误检测与打印：支持 dict 响应和 HTTP 响应对象
                error_msg = None
                # None 或 空响应
                if resp is None:
                    error_msg = "empty response"
                # 字典型响应，Cloudflare SDK/HTTP API 常用字段：'success', 'errors', 'error', 'message'
                elif isinstance(resp, dict):
                    if resp.get('success') is False:
                        error_msg = resp.get('errors') or resp.get('message') or str(resp)
                    elif resp.get('errors'):
                        error_msg = resp.get('errors')
                    elif resp.get('error'):
                        error_msg = resp.get('error')
                # HTTP 响应对象（requests.Response 等）
                elif hasattr(resp, 'status_code'):
                    status = getattr(resp, 'status_code')
                    if status != 200 and status != 201:
                        # 尝试获取文本信息
                        text = getattr(resp, 'text', None) or getattr(resp, 'content', None)
                        error_msg = f"status {status}: {text}"

                if error_msg:
                    print("Error inserting:", error_msg)
                else:
                    print("Inserted successfully:", resp)


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


def parse_youtube_date(date_str):
    """
    将 YouTube 的相对时间字符串转换为 YYYY-MM-DD 格式
    支持: 'Streamed 4 months ago', '2 years ago', '2 days ago', '1 hour ago' 等
    """
    now = datetime.datetime.now()
    
    # 1. 预处理：转为小写并提取数字和单位
    # 使用正则匹配数字和单位（year, month, week, day, hour, minute）
    clean_str = date_str.lower()
    match = re.search(r'(\d+)\s+(year|month|week|day|hour|minute)', clean_str)
    
    if not match:
        return now.strftime('%Y-%m-%d') # 如果没匹配到，默认返回今天
    
    value = int(match.group(1))
    unit = match.group(2)
    
    # 2. 根据单位计算偏移量
    if 'year' in unit:
        delta = relativedelta(years=value)
    elif 'month' in unit:
        delta = relativedelta(months=value)
    elif 'week' in unit:
        delta = relativedelta(weeks=value)
    elif 'day' in unit:
        delta = relativedelta(days=value)
    elif 'hour' in unit:
        delta = relativedelta(hours=value)
    elif 'minute' in unit:
        delta = relativedelta(minutes=value)
    else:
        delta = relativedelta()

    # 3. 计算真实日期
    target_date = now - delta
    return target_date.strftime('%Y-%m-%d')



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