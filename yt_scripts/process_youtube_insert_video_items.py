import argparse
import json
import os
import re
import datetime
from cloudflare import Cloudflare
from dateutil.relativedelta import relativedelta
import sys


from db_utils import query_by_links

def insert_channel_tb(filename, client, database_id, account_id):
    """
    读取 JSONL 文件并将频道数据插入到 youtube_channel_tb 数据库。
    """
    sqls = []
    crawl_pt = extract_date_from_filename(filename)

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line.strip())
                channel_name = data.get('channel_name', '').replace("'", "`")
                channel_url = data.get('channel_url', '').replace("'", "`")
                description = data.get('description', '').replace("'", "`")
                subscribers = data.get('subscribers', 0)
                video_count = data.get('video_count', 0)

                sql = f"""
                INSERT INTO youtube_channel_tb 
                (channel_name, channel_url, description, subscribers, video_count, crawl_pt)
                VALUES ('{channel_name}', '{channel_url}', '{description}', {subscribers}, {video_count}, '{crawl_pt}')
                ON CONFLICT(channel_url, crawl_pt) DO UPDATE SET
                    description = excluded.description,
                    subscribers = excluded.subscribers,
                    video_count = excluded.video_count,
                    updated_at = CURRENT_TIMESTAMP
                """
                sqls.append(sql)

    # 执行批量插入
    resp = client.d1.database.query(
        database_id=database_id,
        account_id=account_id,
        sql=';'.join(sqls)
    )

    # 错误处理
    if resp is None:
        print("Error: Empty response from database.")
    elif isinstance(resp, dict) and not resp.get('success', True):
        print("Error inserting channels:", resp.get('errors', resp))
    else:
        print("Channels inserted/updated successfully.")


def insert_video_tb(filename, client, database_id, account_id):
    # 读取 JSONL 文件
    rank_index = 0
    sqls = []
    with open(filename, 'r', encoding='utf-8') as f:
        crawl_pt = extract_date_from_filename(filename)

        for line in f:
            rank_index += 1
            if line.strip():
                data = json.loads(line.strip())
                # 映射字段
                keyword = data.get('keyword').replace("'", '`')
                crawl_pt =  crawl_pt
                title = data.get('title')
                if title is None:
                    print(f'无法提取该行数据的title：{line}')
                    title = ""
                    # continue
                else:
                    title = title.replace("'", '`')
                channel = data.get('channel').replace("'", '`')
                link = data.get('link')

                platform = data.get('platform')

                if platform == 'youtube':
                    channel_url = data.get('channel_url')
                    views_raw = data.get('views_raw')
                    views_value = data.get('views_value')
                    publish_date_raw = data.get('publish_date_raw')
                    publish_date_clean = parse_youtube_date(data.get('publish_date_clean'))
                    # 构造 SQL
                    sql = f"""
                    INSERT INTO youtube_video_crawl_item_tb 
                    (keyword, crawl_pt, title, link, channel, channel_url, views_raw, views_value, publish_date_raw, publish_date_clean, rank_index, platform)
                    VALUES ('{keyword}', '{crawl_pt}', '{title}', '{link}', '{channel}', '{channel_url}', '{views_raw}', '{views_value}', '{publish_date_raw}', '{publish_date_clean}', '{rank_index}', '{platform}')
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
                        platform = excluded.platform,
                        updated_at = CURRENT_TIMESTAMP
                    """

                    sqls.append(sql)
                elif platform == 'douyin':
                    video_ratio = data.get('video_ratio')
                    video_duration = data.get('video_duration')
                    publish_date_clean = data.get('publish_date_clean')
                    if publish_date_clean is not None:
                        publish_date_clean = unix_to_date(publish_date_clean)
                    else:
                        publish_date_clean = '1970-01-01'
                    digg_count = data.get("digg_count")
                    all_video_urls = data.get("all_video_urls")
                    if isinstance(all_video_urls, list):
                        all_video_urls = ','.join(all_video_urls)
                    play_url = data.get("play_url")
                    sql = f"""
                    INSERT INTO youtube_video_crawl_item_tb 
                    (keyword, crawl_pt, title, link, channel, publish_date_clean, rank_index, digg_count, platform, all_video_urls, play_url, video_ratio, video_duration)
                    VALUES ('{keyword}', '{crawl_pt}', '{title}', '{link}', '{channel}', '{publish_date_clean}', '{rank_index}', '{digg_count}', '{platform}', '{all_video_urls}', '{play_url}', '{video_ratio}', '{video_duration}')
                    ON CONFLICT(keyword, crawl_pt, rank_index, link) DO UPDATE SET
                        title = excluded.title,
                        link = excluded.link,
                        channel = excluded.channel,
                        publish_date_clean = excluded.publish_date_clean,
                        rank_index = excluded.rank_index,
                        digg_count = excluded.digg_count,
                        platform = excluded.platform,
                        all_video_urls = excluded.all_video_urls,
                        play_url = excluded.play_url,
                       video_ratio = excluded.video_ratio,
                      video_duration = excluded.video_duration,
                        updated_at = CURRENT_TIMESTAMP
                    """

                    sqls.append(sql)

                    


        resp = client.d1.database.query(
            database_id=database_id,
            account_id=account_id,
            sql=';'.join(sqls))

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




def unix_to_date(unix_time):
    """
    将 Unix 时间戳（秒）转换为 指定格式的日期字符串
    """
    # 1. 将秒转换为 datetime 对象
    dt_object = datetime.datetime.fromtimestamp(unix_time)
    
    # 2. 格式化为 YYYY-MM-DD
    return dt_object.strftime('%Y-%m-%d')



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
    match = re.search(r'(\d+)\s{0,1}(year|month|week|day|hour|minute|h|mo)', clean_str)
    
    if not match:
        return now.strftime('%Y-%m-%d') # 如果没匹配到，默认返回今天
    
    value = int(match.group(1))
    unit = match.group(2)
    
    # 2. 根据单位计算偏移量
    if 'year' in unit:
        delta = relativedelta(years=value)
    elif 'month' in unit or 'mo' in unit:
        delta = relativedelta(months=value)
    elif 'week' in unit:
        delta = relativedelta(weeks=value)
    elif 'day' in unit:
        delta = relativedelta(days=value)
    elif 'hour' in unit or 'h' in unit:
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

    parser.add_argument("--file_type", required=False, help="video 插入视频信息-搜索结果  channel, channel信息, download  通过url下载视频, ")
    parser.add_argument("--input_file", help="输入文件路径")
    parser.add_argument("--video_path", help="视频下载路径")
    parser.add_argument("--link_ids", help="需要处理的linkid列表，使用逗号分隔")


    args = parser.parse_args()

    # 获取参数
    api_token = args.cf_d1_api_token or os.getenv('CF_D1_API_TOKEN')
    account_id = args.cf_d1_account_id or os.getenv('CF_D1_ACCOUNT_ID')
    database_id = args.cf_d1_database_id or os.getenv('CF_D1_DATABASE_ID')
    file_type = args.file_type
    input_file = args.input_file
    video_path = args.video_path
    link_ids = args.link_ids

    client = Cloudflare(api_token=api_token)
    
    # 检查输入文件是否为空


    if file_type == 'video':
        # 如果传入的是目录，则遍历目录下的 .jsonl/.json 文件逐个插入
        if input_file is None:
            print('input file 不能为空')
            return 

        
        if os.path.isdir(input_file):
            allowed_ext = ('.jsonl', '.json')
            for entry in sorted(os.listdir(input_file)):
                if entry.startswith('.'):
                    continue
                full = os.path.join(input_file, entry)
                if os.path.isfile(full) and full.lower().endswith(allowed_ext):
                    print(f"Processing file: {full}")
                    insert_video_tb(full, client, database_id, account_id)
                else:
                    print(f"Skipping non-json file: {full}")
        else:
            insert_video_tb(input_file, client, database_id, account_id)
    elif file_type == 'channel': # 将channel信息塞入到数据库中
        if os.path.isfile(input_file) and os.path.getsize(input_file) == 0:
            print(f"输入文件 {input_file} 为空，无法处理。")
            return
        insert_channel_tb(input_file, client, database_id, account_id)
    elif file_type == 'download': # 下载视频信息
        # 将对应的图片下载
        if video_path is None or link_ids is None:
            print('video_path links不能为空 ')
            return 
        items = query_by_links(client, database_id, account_id, link_ids)
        for item in items:
            all_video_urls = item['all_video_urls']
            if all_video_urls:
                print(f"All video URLs: {all_video_urls}")
            else:
                print("No video URLs found for this item.")



if __name__ == "__main__":
    main()