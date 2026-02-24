import argparse
from ast import Num
import json
import os
import re
from resource import getrlimit
from turtle import update
from cloudflare import Cloudflare

from src.utils.parse_utils import extract_brand_name, extract_patent_numbers, extract_us_state, is_gemini_ai_resp_array



# 案号格式：如 25-cv-06628、2025-cv-06628（数字-cv-数字）；统一化为 2025-cv-06628（4位年-cv-5位号）
# 24-cv-12815
CASE_NUMBER_PATTERN = re.compile(r"(\d{2,4})-cv-(\d+)", re.IGNORECASE)

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

def select_crawl_item_content(client, account_id, database_id, id=None):
    """执行 SQL：从 tro_crawl_item_tb 查询 id 与 title+content 拼接内容，返回结果列表。"""
    sql = """
    SELECT
      id,
      COALESCE(json_extract(crawl_item, '$.title'), '') as title,
      COALESCE(json_extract(crawl_item, '$.content'), '') AS content,
      COALESCE(json_extract(crawl_item, '$.case_number'), '') AS case_number,
      gemini_ai_resp
      
    FROM tro_crawl_item_tb
    """
    if id is not None:
        sql = sql + f" where id = {id}"
    resp = client.d1.database.query(
        database_id=database_id,
        account_id=account_id,
        sql=sql.strip(),
    )
    # D1 返回结构: resp.result[0].results 为行列表
    if not resp.result or not resp.result[0].results:
        return []
    return [{"id": row["id"], "content": row["content"] or "", "title": row["title"] or "", "case_number": row["case_number"] or "", "gemini_ai_resp": row["gemini_ai_resp"] or ""} for row in resp.result[0].results]


def find_case_numbers(content: str):
    """在 content 中匹配所有案号，统一为 2025-cv-06628 格式后去重返回。"""
    if not content:
        return []
    raw_list = CASE_NUMBER_PATTERN.findall(content)
    # 每组 (year_part, num_part) 转为统一格式
    normalized = [normalize_case_number(f"{y}-cv-{n}") for y, n in raw_list]
    return list[str](dict.fromkeys(normalized))


def update_is_multi_case_number_and_court_info_and_patent_arr(client, account_id, database_id, id=None):
    """
    根据爬取内容中案号数量判断是否多个案号，并更新 is_multi_case_number、case_number_arr 字段（每条 SQL 单独执行）
    更新表中的multi_case相关字段信息；
    更新表中court_info字段
    更新表中brand字段信息
    """
    rows = select_crawl_item_content(client, account_id, database_id, id=id)
    if not rows:
        return []
    results = []
    cnt = 0
    update_sql_arr = []
    update_params_arr = []
    for row in rows:
        cnt += 1
        rid, content, title, case_number, gemini_ai_resp = row["id"], row["content"], row['title'], row['case_number'], row['gemini_ai_resp']

        # 抓取的内容中存在case number
        content_case_numbers = find_case_numbers(content)

        # title 中存在case number
        title_case_number = find_case_numbers(title) 

        # 抓取字段中存在case number
        case_number_list = find_case_numbers(case_number)


        ##########################################
        # 计算is_multi字段数值
        ##########################################
        is_multi = "0"
        if "集合" in title or is_gemini_ai_resp_array(gemini_ai_resp):
            is_multi = "1"

        elif len(title_case_number)  == 1 or len(case_number_list) == 1:
            is_multi = "0"
        elif len(content_case_numbers) > 30:
            is_multi = "1"
        elif len(title_case_number) + len(content_case_numbers) < 1:
            is_multi = "-1"
        if gemini_ai_resp is not None:
            idx1 = str(gemini_ai_resp).find('{')
            idx2 = str(gemini_ai_resp).find('[')
            if idx2 != -1 and idx2 < idx1:
                is_multi = '1'
            
        # if len(content_case_numbers) > 15:
        #     print(rid)

        # case_numbers = content_case_numbers + title_case_number + case_number_list
        # case_number_arr_json = json.dumps(case_numbers, ensure_ascii=False)
        # title_case_number_json = ','.join(title_case_number)

        case_num_json = {'content_case_numbers': content_case_numbers, 'title_case_number': title_case_number,
                         'origin_case_number': case_number_list}
        case_number_arr_json = ','.join(content_case_numbers+title_case_number+case_number_list)
        
        results.append({"id": rid, "is_multi_case_number": is_multi, "case_numbers": content_case_numbers+title_case_number+case_number_list})
        # case_number_arr_json = json.dumps(case_num_json) 
        # print(json.dumps(case_num_json))

        ##########################################
        # 计算extract_case_number字段逻辑
        ##########################################
        extract_case_num_column = ''
        if case_number_list is not None and len(case_number_list) > 0:
            extract_case_num_column = case_number_list[0]
        elif title_case_number is not None and len(title_case_number) > 0:
            extract_case_num_column = title_case_number[0]
        elif content_case_numbers is not None and len(content_case_numbers) > 0:
            extract_case_num_column = content_case_numbers[0]
        # print(extract_case_num_column)
        
        
        a = ','.join(title_case_number)
        b = ','.join(content_case_numbers)
        c = ','.join(case_number_list)

        
        ##########################################
        # 提取court信息
        ##########################################
        court_info = extract_us_state(content) 
        if court_info is None:
            court_info = ''

        ##########################################
        # 提取patent信息
        ##########################################
        patent_info = extract_patent_numbers(content, True)
        d = ','.join(patent_info)

        ##########################################
        # 提取brand信息
        ##########################################
        brand, brand_info = extract_brand_name(gemini_ai_resp)
        
    
        ##########################################
        # 生成更新的 sql 参数并加入批次（参数化执行，避免注入与引号问题）
        ##########################################
        one_sql = (
            "UPDATE tro_crawl_item_tb SET "
            "is_multi_case_number = ?, extract_case_number = ?, case_number_arr = ?, "
            "title_case_arr = ?, content_case_arr = ?, origin_case_arr = ?, "
            "extract_court = ?, patent_arr = ?, brand = ?, brand_info = ? "
            "WHERE id = ?"
        )
        update_sql_arr.append(one_sql)
        update_params_arr.append(
            (
                is_multi,
                extract_case_num_column or "",
                case_number_arr_json or "",
                a or "",
                b or "",
                c or "",
                court_info or "",
                d or "",
                brand or "",
                brand_info or "",
                rid,
            )
        )

        if cnt % UPDATE_BATCH_SIZE == 0 or cnt == len(rows):
            try:
                batch_sql = "; ".join(update_sql_arr)
                batch_params = [p for params in update_params_arr for p in params]
                client.d1.database.query(
                    database_id=database_id,
                    account_id=account_id,
                    sql=batch_sql,
                    params=batch_params,
                )
            except Exception as e:
                print("sql:", "; ".join(update_sql_arr)[:200], "...")
                print(str(e))
                # results[-1]["error"] = str(e)
            finally:
                update_sql_arr = []
                update_params_arr = []
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
    # print(find_case_numbers("TRO案例24-cv-12815：Nanoblock 积木商标维权！"))

    
    # for debug
    # result = update_is_multi_case_number_and_court_info_and_patent_arr(client, account_id, database_id, id=34)
    result = update_is_multi_case_number_and_court_info_and_patent_arr(client, account_id, database_id)
    print(f"共处理 {len(result)} 条")
    for row in result:
        cases = row.get("case_numbers", [])
        multi = row.get("is_multi_case_number", "")
        err = row.get("error", "")
        # if multi == "1" or len(cases) >= 10:
        msg = f"  id={row['id']}, is_multi_case_number={multi}, 案号数={len(cases)}"
        if cases:
            msg += f", 案号={cases[:5]}{'...' if len(cases) > 5 else ''}"
        if err:
            msg += f", error={err}"
            print(msg)
    return result


if __name__ == "__main__":
    main()