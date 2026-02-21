import argparse
import json
import os
import re
from cloudflare import Cloudflare



# 案号格式：如 25-cv-06628、2025-cv-06628（数字-cv-数字）；统一化为 2025-cv-06628（4位年-cv-5位号）
CASE_NUMBER_PATTERN = re.compile(r"\b(\d{2,4})-cv-(\d+)\b", re.IGNORECASE)

# 每批执行的 UPDATE 条数
UPDATE_BATCH_SIZE = 50


def normalize_case_number(raw: str) -> str:
    """将案号统一为 2025-cv-06628 格式：4 位年份 + -cv- + 5 位数字（前导零）。"""
    m = CASE_NUMBER_PATTERN.fullmatch(raw.strip())
    if not m:
        return raw
    year_str, num_str = m.group(1), m.group(2)
    # 年份：2 位按 20xx，3/4 位前补零到 4 位
    if len(year_str) == 2:
        year = "20" + year_str
    else:
        year = year_str.zfill(4)
    # 案号数字：前导零补足 5 位
    num = num_str.zfill(5)
    return f"{year}-cv-{num}"

def select_crawl_item_content(client, account_id, database_id):
    """执行 SQL：从 tro_crawl_item_tb 查询 id 与 title+content 拼接内容，返回结果列表。"""
    sql = """
    SELECT
      id,
      COALESCE(json_extract(crawl_item, '$.title'), '') as title,
      COALESCE(json_extract(crawl_item, '$.content'), '') AS content
    FROM tro_crawl_item_tb
    """
    resp = client.d1.database.query(
        database_id=database_id,
        account_id=account_id,
        sql=sql.strip(),
    )
    # D1 返回结构: resp.result[0].results 为行列表
    if not resp.result or not resp.result[0].results:
        return []
    return [{"id": row["id"], "content": row["content"] or ""} for row in resp.result[0].results]


def find_case_numbers(content: str):
    """在 content 中匹配所有案号，统一为 2025-cv-06628 格式后去重返回。"""
    if not content:
        return []
    raw_list = CASE_NUMBER_PATTERN.findall(content)
    # 每组 (year_part, num_part) 转为统一格式
    normalized = [normalize_case_number(f"{y}-cv-{n}") for y, n in raw_list]
    return list[str](dict.fromkeys(normalized))


def update_is_multi_case_number(client, account_id, database_id):
    """根据爬取内容中案号数量判断是否多个案号，并更新 is_multi_case_number、case_number_arr 字段（每条 SQL 单独执行）。"""
    rows = select_crawl_item_content(client, account_id, database_id)
    if not rows:
        return []
    results = []
    update_sql = "UPDATE tro_crawl_item_tb SET is_multi_case_number = ?, case_number_arr = ? WHERE id = ?"
    cnt = 0
    update_sql_arr = []
    for row in rows:
        cnt += 1
        rid, content, title = row["id"], row["content"], row['title']
        content_case_numbers = find_case_numbers(content)
        title_case_number = find_case_numbers(title) 

        is_multi = "0"
        if "集合" in title:
            is_multi = "1"
            print(rid)
        elif len(title_case_number)  == 1:
            is_multi = "0"
        
        if len(content_case_numbers) > 15:
            print(rid)

        # case_number_arr_json = json.dumps(case_numbers, ensure_ascii=False)
        case_number_arr_json = ','.join(content_case_numbers)
        results.append({"id": rid, "is_multi_case_number": is_multi, "case_numbers": content_case_numbers})
        update_sql = f'UPDATE tro_crawl_item_tb SET is_multi_case_number = {is_multi}, case_number_arr = "{case_number_arr_json}" WHERE id = {rid}'
        update_sql_arr.append(update_sql)


        # if cnt % UPDATE_BATCH_SIZE == 0 or cnt == len(rows):
        #     print(f"进度: {cnt}/{len(rows)} ({cnt/len(rows)*100:.2f}%)")
        #     # print(';'.join(update_sql_arr))
        #     try:
        #         client.d1.database.query(
        #             database_id=database_id,
        #             account_id=account_id,
        #             sql=';'.join(update_sql_arr),
        #         )
        #     except Exception as e:
        #         results[-1]["error"] = str(e)
        #     finally:
        #         update_sql_arr = []
    return results

def main():
    parser = argparse.ArgumentParser(description="tro_crawl_item 查询与处理")
    parser.add_argument("--cf_d1_api_token", required=False, help="Cloudflare D1 API Token，可通过环境变量 CF_D1_API_TOKEN 传递")
    parser.add_argument("--cf_d1_account_id", required=False, help="Cloudflare D1 ACCOUNT_ID，可通过环境变量 CF_D1_ACCOUNT_ID 传递")
    parser.add_argument("--cf_d1_database_id", required=False, help="Cloudflare D1 DATABASE_ID，可通过环境变量 CF_D1_DATABASE_ID 传递")
    args = parser.parse_args()

    token = args.cf_d1_api_token or os.getenv("CF_D1_API_TOKEN")
    account_id = args.cf_d1_account_id or os.getenv("CF_D1_ACCOUNT_ID")
    database_id = args.cf_d1_database_id or os.getenv("CF_D1_DATABASE_ID")
    if not all([token, account_id, database_id]):
        print("缺少 D1 配置，请提供 --cf_d1_* 或环境变量 CF_D1_API_TOKEN / CF_D1_ACCOUNT_ID / CF_D1_DATABASE_ID")
        return

    client = Cloudflare(api_token=token)
    result = update_is_multi_case_number(client, account_id, database_id)
    print(f"共处理 {len(result)} 条")
    for row in result:
        cases = row.get("case_numbers", [])
        multi = row.get("is_multi_case_number", "")
        err = row.get("error", "")
        msg = f"  id={row['id']}, is_multi_case_number={multi}, 案号数={len(cases)}"
        if cases:
            msg += f", 案号={cases[:5]}{'...' if len(cases) > 5 else ''}"
        if err:
            msg += f", error={err}"
        print(msg)
    return result


if __name__ == "__main__":
    main()