import argparse
import os
import re
from dotenv import load_dotenv

load_dotenv()

# 案号格式：如 25-cv-06628、2025-cv-06628（数字-cv-数字）
CASE_NUMBER_PATTERN = re.compile(r"\b\d{2,4}-cv-\d{4,}\b", re.IGNORECASE)


def select_crawl_item_content(client, account_id, database_id):
    """执行 SQL：从 tro_crawl_item_tb 查询 id 与 title+content 拼接内容，返回结果列表。"""
    sql = """
    SELECT
      id,
      (COALESCE(json_extract(crawl_item, '$.title'), '') || COALESCE(json_extract(crawl_item, '$.content'), '')) AS content
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
    """在 content 中匹配所有案号（如 25-cv-06628、2025-cv-06628），返回去重后的列表。"""
    if not content:
        return []
    return list(dict.fromkeys(CASE_NUMBER_PATTERN.findall(content)))


def update_is_multi_case_number(client, account_id, database_id):
    """根据爬取内容中案号数量判断是否多个案号，并批量更新 is_multi_case_number 字段。"""
    rows = select_crawl_item_content(client, account_id, database_id)
    if not rows:
        return []
    # 先计算每条记录的案号与 is_multi，并收集结果
    results = []
    id_to_value = []  # [(id, is_multi), ...]
    for row in rows:
        rid, content = row["id"], row["content"]
        case_numbers = find_case_numbers(content)
        is_multi = "1" if len(case_numbers) >= 2 else "0"
        results.append({"id": rid, "is_multi_case_number": is_multi, "case_numbers": case_numbers})
    print(results)
    #     id_to_value.append((rid, is_multi))
    # # 批量 UPDATE：CASE id WHEN ? THEN ? ... END WHERE id IN (?, ...)
    # case_parts = [" WHEN ? THEN ?"] * len(id_to_value)
    # case_sql = "".join(case_parts)
    # placeholders = ", ".join(["?"] * len(id_to_value))
    # update_sql = f"UPDATE tro_crawl_item_tb SET is_multi_case_number = CASE id{case_sql} END WHERE id IN ({placeholders})"
    # params = []
    # for rid, val in id_to_value:
    #     params.extend([rid, val])
    # params.extend([rid for rid, _ in id_to_value])
    # try:
    #     client.d1.database.query(
    #         database_id=database_id,
    #         account_id=account_id,
    #         sql=update_sql,
    #         params=params,
    #     )
    # except Exception as e:
    #     err_msg = str(e)
    #     for r in results:
    #         r["error"] = err_msg
    # return results

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

    from cloudflare import Cloudflare
    client = Cloudflare(api_token=token)
    result = update_is_multi_case_number(client, account_id, database_id)
    # print(f"共处理 {len(result)} 条")
    # for row in result:
    #     cases = row.get("case_numbers", [])
    #     multi = row.get("is_multi_case_number", "")
    #     err = row.get("error", "")
    #     msg = f"  id={row['id']}, is_multi_case_number={multi}, 案号数={len(cases)}"
    #     if cases:
    #         msg += f", 案号={cases[:5]}{'...' if len(cases) > 5 else ''}"
    #     if err:
    #         msg += f", error={err}"
    #     print(msg)
    return result


if __name__ == "__main__":
    main()