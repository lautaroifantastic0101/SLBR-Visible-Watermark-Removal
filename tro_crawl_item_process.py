import argparse
from ast import Num
import copy
import json
import os
import re
from resource import getrlimit
from turtle import up, update
from cloudflare import Cloudflare
from numpy.random.mtrand import f
from rapidfuzz import process
from sympy import preorder_traversal
from sympy.simplify.fu import process_common_addends

from src.ai_utils.ai_utils import summarise_case
from src.utils.parse_utils import extract_brand_name, extract_copyright_numbers, extract_law_type_info, extract_patent_numbers, extract_us_state, is_gemini_ai_resp_array



# 案号格式：如 25-cv-06628、2025-cv-06628（数字-cv-数字）；统一化为 2025-cv-06628（4位年-cv-5位号）
# 24-cv-12815
CASE_NUMBER_PATTERN = re.compile(r"(\d{2,4})-cv-(\d{3,5})", re.IGNORECASE)

# 每批执行的 UPDATE 条数
UPDATE_BATCH_SIZE = 100


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

def select_crawl_item_content(client, account_id, database_id, id=None, start_pt=None, end_pt=None, source_types=None):
    """执行 SQL：从 tro_crawl_item_tb 查询 id 与 title+content 拼接内容，返回结果列表。
    source_types: 逗号分隔的 source_type 列表，如 'CifTRONewsItem,MaijiaxingiquTRONewsItem'；默认使用 CifTRONewsItem, MaijiaxingiquTRONewsItem, QqdipTROItem, RuiguanTROItem
    """
    if source_types is None or (isinstance(source_types, str) and not source_types.strip()):
        source_list = ["CifTRONewsItem", "MaijiaxingiquTRONewsItem", "QqdipTROItem", "RuiguanTROItem"]
    else:
        source_list = [s.strip() for s in str(source_types).split(",") if s.strip()]
    in_clause = ", ".join(f"'{s}'" for s in source_list)
    sql = f"""
    SELECT
      id,
      origin_article_id,
      COALESCE(json_extract(crawl_item, '$.title'), '') as title,
      COALESCE(json_extract(crawl_item, '$.content'), '') AS content,
      COALESCE(json_extract(crawl_item, '$.case_number'), '') AS case_number,
      gemini_ai_resp
    FROM tro_crawl_item_tb
    WHERE  source_type in ({in_clause})
    """
    # and gemini_ai_resp is not null 
    if id is not None:
        sql = sql + f" and id IN ({id})"
    
    if start_pt and end_pt:
        sql = sql + f" and created_at between '{start_pt}' and  '{end_pt}'"
    
    print(sql)
    resp = client.d1.database.query(
        database_id=database_id,
        account_id=account_id,
        sql=sql.strip(),
    )
    # D1 返回结构: resp.result[0].results 为行列表
    if not resp.result or not resp.result[0].results:
        return []
    return [{"id": row["id"], "content": row["content"] or "", "title": row["title"] or "", "case_number": row["case_number"] or "", "gemini_ai_resp": row["gemini_ai_resp"] or "", "origin_article_id":row["origin_article_id"] or ""} for row in resp.result[0].results]


def find_case_numbers(content: str):
    """在 content 中匹配所有案号，统一为 2025-cv-06628 格式后去重返回。"""
    if not content:
        return []
    raw_list = CASE_NUMBER_PATTERN.findall(content)
    # 每组 (year_part, num_part) 转为统一格式
    normalized = [normalize_case_number(f"{y}-cv-{n}") for y, n in raw_list]
    return list[str](dict.fromkeys(normalized))


def complete_basic_info_columns(rows, id=None):
    """
    根据爬取内容中案号数量判断是否多个案号，并更新 is_multi_case_number、case_number_arr 字段（每条 SQL 单独执行）
    更新表中的multi_case相关字段信息；
    更新表中court_info字段
    更新表中brand字段信息
    """
    with open('config/preprocess_config.json', 'r', encoding='utf-8') as f:
        preprocess_config = json.load(f)
    if not rows:
        return []
    results = []
    cnt = 0
    update_sql_arr = []
    # update_params_arr = []
    for row in rows:
        cnt += 1
        rid, content, title, case_number, gemini_ai_resp, origin_article_id = row["id"], row["content"], row['title'], row['case_number'], row['gemini_ai_resp'], row['origin_article_id']

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

        ##########################################
        # 计算extract_case_number字段逻辑
        ##########################################
        # case_numbers = content_case_numbers + title_case_number + case_number_list
        # case_number_arr_json = json.dumps(case_numbers, ensure_ascii=False)
        # title_case_number_json = ','.join(title_case_number)

        case_num_json = {'content_case_numbers': content_case_numbers, 'title_case_number': title_case_number,
                         'origin_case_number': case_number_list}
        case_number_arr_json = ','.join(content_case_numbers+title_case_number+case_number_list)
        
        results.append({"id": rid, "is_multi_case_number": is_multi, "case_numbers": content_case_numbers+title_case_number+case_number_list})
        # case_number_arr_json = json.dumps(case_num_json) 
        # print(json.dumps(case_num_json))

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
        # 提取patent信息 包括 版权信息
        ##########################################
        patent_info = extract_patent_numbers(content, True)
        copyright_info = extract_copyright_numbers(content, True)
        patent_info.extend(copyright_info)
        d = json.dumps(patent_info)

        ##########################################
        # 提取brand信息
        ##########################################
        brand, brand_info, brand_website = extract_brand_name(gemini_ai_resp)
        # print(brand, brand_info)

        
        ##########################################
        # 维权信息处理
        ##########################################
        law_type = extract_law_type_info(gemini_ai_resp)


        ##########################################
        # 生成更新的 sql 参数并加入批次（参数化执行，避免注入与引号问题）
        ##########################################
        if origin_article_id in preprocess_config:
            config = preprocess_config[origin_article_id]
            if 'brand' in config:
                brand = config['brand']
            if 'case_number_arr' in config:
                case_number_arr_json = config['case_number_arr']
            
        tmp_sql = (
            "UPDATE tro_crawl_item_tb SET "
            f"is_multi_case_number = '{is_multi}', extract_case_number = '{extract_case_num_column}', case_number_arr = '{case_number_arr_json}', "
           f"title_case_arr = '{a}', content_case_arr = '{b}', origin_case_arr = '{c}', "
            f"extract_court = '{court_info}', patent_arr = '{d}', brand = '{brand}', brand_info = '{brand_info}', brand_website = '{brand_website}', violation_type = '{law_type}', "
            f"updated_at = datetime('now') "
            f"WHERE id = {rid};"
        )
        # print(tmp_sql)

        # update_sql_arr.append(one_sql)
        update_sql_arr.append(tmp_sql)
        # update_params_arr.append(
        #     (
        #         is_multi,
        #         extract_case_num_column or "",
        #         case_number_arr_json or "",
        #         a or "",
        #         b or "",
        #         c or "",
        #         court_info or "",
        #         d or "",
        #         brand or "",
        #         brand_info or "",
        #         rid,
        #     )
        # )
    return update_sql_arr
    # return update_sql_arr, update_params_arr
    # return results

def complete_case_brief_column(account_id, cf_ai_api_token, rows):
    """更新brief 字段

    Args:
        rows (_type_): _description_
        
    return : 需要执行的update sqls
    """
    if not rows:
        return []
    cnt = 0
    update_sql_arr = []
    # update_params_arr = []
    for row in rows:
        cnt += 1
        rid, content = row["id"], row["content"]
        case_brief = summarise_case(account_id, cf_ai_api_token, content)
        print("case brief", case_brief)
        tmp_sql = (
            "UPDATE tro_crawl_item_tb SET "
            f"case_brief = '{case_brief}'  , updated_at = CURRENT_TIMESTAMP "
            f"WHERE id = {rid};"
        )
        update_sql_arr.append(tmp_sql)

    return update_sql_arr



def main():
    parser = argparse.ArgumentParser(description="tro_crawl_item 查询与处理")
    parser.add_argument("--cf_d1_api_token", required=False, help="Cloudflare D1 API Token，可通过环境变量 CF_D1_API_TOKEN 传递")
    parser.add_argument("--cf_ai_api_token", required=False, help="Cloudflare AI API Token，可通过环境变量 CF_D1_API_TOKEN 传递")
    parser.add_argument("--cf_d1_account_id", required=False, help="Cloudflare D1 ACCOUNT_ID，可通过环境变量 CF_D1_ACCOUNT_ID 传递")
    parser.add_argument("--cf_d1_database_id", required=False, help="Cloudflare D1 DATABASE_ID，可通过环境变量 CF_D1_DATABASE_ID 传递")
    parser.add_argument("--start_pt", required=False, type=str, help="处理开始点，可选")
    parser.add_argument("--end_pt", required=False, type=str, help="处理结束点，可选")
    parser.add_argument("--row_ids", required=False, help="以逗号分隔的待处理的row id列表，如: 123,456,789")
    parser.add_argument("--source_types", required=False, type=str, default="CifTRONewsItem,MaijiaxingiquTRONewsItem,QqdipTROItem,RuiguanTROItem", help="逗号分隔的 source_type 列表，如: CifTRONewsItem,QqdipTROItem")
    parser.add_argument("--update_case_brief", action="store_true", help="只是更新case_brief字段")
    args = parser.parse_args()


    token = args.cf_d1_api_token or os.getenv("CF_D1_API_TOKEN")
    account_id = args.cf_d1_account_id or os.getenv("CF_D1_ACCOUNT_ID")
    database_id = args.cf_d1_database_id or os.getenv("CF_D1_DATABASE_ID")
    cf_ai_api_token = args.cf_ai_api_token

    row_ids = args.row_ids
    start_pt = args.start_pt
    end_pt = args.end_pt
    source_types = args.source_types

    update_case_brief = args.update_case_brief

    if not all([token, account_id, database_id, cf_ai_api_token]):
        print("缺少 D1 配置，请提供 --cf_d1_* 或环境变量 CF_D1_API_TOKEN / CF_D1_ACCOUNT_ID / CF_D1_DATABASE_ID")
        return

    client = Cloudflare(api_token=token)
    # print(find_case_numbers("TRO案例24-cv-12815：Nanoblock 积木商标维权！"))
    
    # for debug
    # result = update_is_multi_case_number_and_court_info_and_patent_arr(client, account_id, database_id, id=34)
    rows = select_crawl_item_content(client, account_id, database_id, id=row_ids, start_pt=start_pt, end_pt=end_pt, source_types=source_types)
    print(f"一共筛选出来行数：{len(rows)}")


    if update_case_brief:
        print("只是更新case_brief字段")
        update_sqls = complete_case_brief_column(account_id, cf_ai_api_token, rows)
        # print(update_sqls)
        # return 
        
        
    else:
        update_sqls = complete_basic_info_columns(rows)
        

    print(f"共处理 {len(update_sqls)} 条")

    ################################################################
    # 开始批量执行sql
    ################################################################
    
    update_sql_arr = []
    cnt = 0
    for sql in update_sqls:
        update_sql_arr.append(sql)
        cnt += 1
        if cnt % UPDATE_BATCH_SIZE == 0 or cnt == len(rows):
            try:
                batch_sql = "; ".join(update_sql_arr)
                client.d1.database.query(
                    database_id=database_id,
                    account_id=account_id,
                    sql=batch_sql,
                )
            except Exception as e:
                print("sql:", "; ".join(update_sql_arr)[:200], "...")
                print(str(e))
                # results[-1]["error"] = str(e)
            finally:
                update_sql_arr = []

if __name__ == "__main__":
    main()
