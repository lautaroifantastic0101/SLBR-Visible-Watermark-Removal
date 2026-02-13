import argparse
import json
from numbers import Real
import os
import re
from dotenv import load_dotenv

load_dotenv()

# tro_crawl_item_tb 字段（与 sql/tro_crawl_item_tb.sql 一致）
TRO_CRAWL_ITEM_COLUMNS = [
    "id", "origin_article_id", "crawl_item", "gemini_ai_resp", "created_at",
    "source_type", "extract_case_number", "extract_court", "is_multi_case_number",
    "ai_model", "updated_at", "case_number_arr",
]

SELECT_JOIN_SQL = """
SELECT
  a.id,
  a.origin_article_id,
  a.crawl_item,
  a.gemini_ai_resp,
  a.created_at,
  a.source_type,
  a.extract_case_number,
  a.extract_court,
  a.is_multi_case_number,
  a.ai_model,
  a.updated_at,
  a.case_number_arr,
  b.crawl_item AS basic_info,
  c.crawl_item AS timeline_info,
  d.new_url_arr,
  d.img_type_arr
FROM (
  SELECT
    id, origin_article_id, crawl_item, gemini_ai_resp, created_at,
    source_type, extract_case_number, extract_court, is_multi_case_number,
    ai_model, updated_at, case_number_arr
  FROM tro_crawl_item_tb
  WHERE source_type = ?
    AND is_multi_case_number = '0'
    AND extract_case_number IS NOT NULL
) a
LEFT OUTER JOIN (
  SELECT id, crawl_item, extract_case_number
  FROM tro_crawl_item_tb
  WHERE source_type IN ('PgprintsTROItem')
) b ON a.extract_case_number = b.extract_case_number
LEFT OUTER JOIN (
  SELECT id, crawl_item, extract_case_number
  FROM tro_crawl_item_tb
  WHERE source_type IN ('Tro61TROItem')
    AND is_multi_case_number = '0'
    AND extract_case_number IS NOT NULL
) c ON a.extract_case_number = TRIM(c.extract_case_number)
LEFT OUTER JOIN (
  SELECT
    origin_post_id,
    GROUP_CONCAT(new_url) AS new_url_arr,
    GROUP_CONCAT(img_type) AS img_type_arr
  FROM tro_post_img
  WHERE source_type = ?
  GROUP BY origin_post_id
) d ON a.origin_article_id = d.origin_post_id
"""


def run_select_join(client, account_id, database_id, source_type: str):
    """执行联表查询，返回结果行列表。source_type 用于过滤主表 a 与图片表 d。"""
    resp = client.d1.database.query(
        database_id=database_id,
        account_id=account_id,
        sql=SELECT_JOIN_SQL.strip(),
        params=[source_type, source_type],
    )
    if not resp.result or not resp.result[0].results:
        return []
    return [dict(row) for row in resp.result[0].results][:5]


def _parse_json_text(s: str):
    """解析可能是纯 JSON 或 ```json ... ``` 包裹的字符串。"""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    return None


def _normalize_date(s: str):
    """将常见日期格式转为 Sanity 需要的 YYYY-MM-DD。"""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    # "日期：02/13/2025" -> 02/13/2025
    if "：" in s or ":" in s:
        s = s.split("：")[-1].split(":")[-1].strip()
    # 2025-2-12 -> 2025-02-12
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", s):
        parts = s.split("-")
        return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    # 02/13/2025 或 13/02/2025（日/月/年 或 月/日/年，按常见 US 月/日/年）
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s):
        parts = s.split("/")
        # 若第一位>12 则为 日/月/年
        if int(parts[0]) > 12:
            return f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
        return f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else None


def _related_cases_list(val) -> list[str]:
    """
    主要元素：name\contact\description 
    将 关联案件 / case_number_arr 转为字符串数组。"""

    if not val:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x]
    if isinstance(val, str):
        try:
            data = json.loads(val)
            return [str(x).strip() for x in (data if isinstance(data, list) else [data]) if x]
        except (json.JSONDecodeError, TypeError):
            return [x.strip() for x in val.split(",") if x.strip()]
    return []


def _parse_brand_info(gemini_info,basic_info,timeline_info) -> str:
    """将品牌信息转为 JSON 字符串。"""
    brand_ret = {}
    gemini_brand = gemini_info and gemini_info.get("品牌方")
    basic_brand = basic_info and basic_info.get("brand")

    
    if gemini_info and gemini_info.get("品牌方信息"):
        brand_info = gemini_info.get("品牌方信息")
        brand_ret["description"] = brand_info
    # elif basic_info and basic_info.get("brand"):
    #     brand_info = json.loads(basic_info.get("brand"))
    # elif timeline_info and timeline_info.get("brand"):
    #     brand_info = json.loads(timeline_info.get("brand"))

    brand_ret["name"] = gemini_brand or basic_brand 
    brand_ret["contact"] = ''
    return json.dumps(brand_ret, ensure_ascii=False) if brand_ret else ''
    


def _parse_timeline_info(timeline_info) -> str:
    """将时间线信息转为字典。"""
    timeline_ret = [] 
    progress = timeline_info and timeline_info.get("progress")
    if progress:
        for item in progress:
            timeline_ret.append({
                "date": item.get("time"),
                "description": item.get("event")
            })
    return json.dumps(timeline_ret)


def row_to_tro_post_doc(row: dict) -> dict:
    """综合 row（a 表 + case_detail_info + case_detail_info2 + gemini_ai_resp）得到 Sanity tro_post 文档。"""
    # 1) gemini_ai_resp（见 tmp/gemini_ai_resp_sample.txt）：案件标题、案件编号、起诉日期、原告、律所、维权类型、品牌方、品牌方信息、涉及的商品类型、关联案件
    gemini = _parse_json_text(row.get("gemini_ai_resp") or "")
    # 2) case_detail_info（b.crawl_item，见 tmp/basic_info_sample.json）：PgprintsTROItem - prosecution_time, case_number, law_firm, brand
    basic = _parse_json_text(row.get("case_detail_info") or "")
    # 3) case_detail_info2（c.crawl_item，见 tmp/timeline_info_sample.json）：Tro61TROItem - title, case_number, release_time, court, brand, law_firm, full_timelines
    timeline_info = _parse_json_text(row.get("timeline_info") or "")
    # 4) a 表 crawl_item
    crawl = _parse_json_text(row.get("crawl_item") or "") or {}

    def _str(v, default=None):
        if v is None or v == "":
            return default
        s = str(v).strip()
        return s if s else default

    # 优先级：gemini > timeline > basic > crawl > row 直字段
    case_number = _str(gemini and gemini.get("案件编号")) or _str(timeline_info and timeline_info.get("case_number")) or _str(basic and basic.get("case_number")) or _str(row.get("extract_case_number"))
    title = _str(gemini and gemini.get("案件标题")) or _str(timeline_info and timeline_info.get("title")) or _str(crawl.get("title"))
    law_date_raw = _str(gemini and gemini.get("起诉日期")) or _str(timeline_info and timeline_info.get("release_time")) or _str(basic and basic.get("prosecution_time")) or _str(crawl.get("lawDate") or crawl.get("law_date"))
    law_date = _normalize_date(law_date_raw) if law_date_raw else None
    law_from = _str(gemini and gemini.get("原告")) or _str(crawl.get("lawFrom") or crawl.get("law_from"))

    # 判断brand是否为全部大写，如果不是，则转为所有单词首字母大写
    if law_from and not law_from.isupper():
        law_from = law_from.title()
    
    law_firm = _str(gemini and gemini.get("律所")) or _str(timeline_info and timeline_info.get("law_firm")) or _str(basic and basic.get("law_firm")) or _str(crawl.get("lawFirm") or crawl.get("law_firm"))
    law_type = _str(gemini and gemini.get("维权类型")) or _str(crawl.get("lawType") or crawl.get("law_type"))
    brand = _str(gemini and gemini.get("品牌方")) or _str(timeline_info and timeline_info.get("brand")) or _str(basic and basic.get("brand")) or _str(crawl.get("brand"))
    # 判断brand是否为全部大写，如果不是，则转为所有单词首字母大写
    if brand and not brand.isupper():
        brand = brand.title()
    brand = 'Elaine Kay Maier' # 用作测试 

    # brand_info = _str(gemini and gemini.get("品牌方信息")) or _str(crawl.get("brandInfo") or crawl.get("brand_info"))
    brand_info = _parse_brand_info(gemini,basic,timeline_info)
    court_info = _str(timeline_info and timeline_info.get("court")) or _str(row.get("extract_court"))
    goods_categories = _str(gemini and gemini.get("涉及的商品类型")) or _str(crawl.get("goodsCategories") or crawl.get("goods_categories"))
    if goods_categories and goods_categories.startswith(('{', '[')) and goods_categories.endswith(('}', ']')):
        try:
            goods_categories = json.loads(goods_categories)
        except Exception as e:
            print(f"error: {e}")
        
    
    
    timeline_info = _parse_timeline_info(timeline_info)


    # relatedCases：gemini 关联案件 > case_number_arr
    related = _related_cases_list(gemini and gemini.get("关联案件")) if gemini else []
    if not related and row.get("case_number_arr"):
        related = _related_cases_list(row["case_number_arr"])
    related = [x for x in related if x] or None
    related = json.dumps(related)
    

    # # content：品牌方信息 + 风险提示（gemini）+ 可选 timeline 摘要
    # content_parts = []
    # if brand_info:
    #     content_parts.append(brand_info)
    # if gemini and _str(gemini.get("风险提示")):
    #     content_parts.append(_str(gemini.get("风险提示")))

    # content = "\n\n".join(content_parts) if content_parts else _str(crawl.get("content"))
    content = ''

    # 图片：new_url_arr / img_type_arr，按 type 合并为 {"type_a": ["url1", "url2"], "type_b": ["url3"]}
    images = {}
    new_url_arr = (row.get("new_url_arr") or "").strip()
    img_type_arr = (row.get("img_type_arr") or "").strip()
    if new_url_arr:
        urls = [u.strip() for u in new_url_arr.split(",") if u.strip()]
        types = [t.strip() for t in img_type_arr.split(",") if t.strip()] if img_type_arr else []
        for i in range(len(urls)):
            t = types[i] if i < len(types) else ""
            key = t if t else "default"
            if key not in images:
                images[key] = []
            images[key].append(urls[i])



    doc = {
        "_id": case_number,
        "caseNumber": case_number,
        "title": title,
        "content": content,
        "brand": brand,
        "brandInfo": brand_info,
        "lawDate": law_date,
        "lawFrom": law_from,
        "lawFirm": law_firm,
        "lawType": law_type,
        "courtInfo": court_info,
        "relatedCases": related,
        "goodsCategories": goods_categories,
        "images": json.dumps(images, ensure_ascii=False) if images else None,  # {"type_a": ["url1","url2"], ...}
        "timeline": timeline_info,
    }
    return {k: v for k, v in doc.items() if v is not None}


def create_sanity_doc(rows: list, project_id: str, dataset: str, token: str, dry_run: bool = False):
    """将查询结果按 tro_post schema 写入 Sanity。dry_run 仅打印不请求。"""
    import requests
    base = f"https://{project_id}.api.sanity.io/v2022-03-07/data/mutate/{dataset}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    created = 0
    errors = []
    for i, row in enumerate(rows):
        doc = row_to_tro_post_doc(row)
        payload = {"mutations": [{"createOrReplace": {"_type": "tro_post", **doc}}]}
        if dry_run:
            print(f"  [dry_run] {i+1} caseNumber={doc.get('caseNumber')} title={doc.get('title', '')[:40]}...")
            created += 1
            continue
        try:
            r = requests.post(base, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            created += 1
            if (i + 1) % 10 == 0:
                print(f"  已上传 {i+1}/{len(rows)} 条")
        except Exception as e:
            errors.append({"index": i + 1, "caseNumber": doc.get("caseNumber"), "error": str(e)})
    if errors:
        print(f"  失败 {len(errors)} 条: {errors}")
    print(f"  完成: 成功 {created}/{len(rows)} 条")
    return created


def main():
    parser = argparse.ArgumentParser(description="tro_crawl_item 联表查询，结果可塞入 Sanity doc")
    parser.add_argument("--cf_d1_api_token", required=False, help="Cloudflare D1 API Token，可通过环境变量 CF_D1_API_TOKEN 传递")
    parser.add_argument("--cf_d1_account_id", required=False, help="Cloudflare D1 ACCOUNT_ID，可通过环境变量 CF_D1_ACCOUNT_ID 传递")
    parser.add_argument("--cf_d1_database_id", required=False, help="Cloudflare D1 DATABASE_ID，可通过环境变量 CF_D1_DATABASE_ID 传递")
    parser.add_argument("--source_type", default="CifTRONewsItem", help="主表与图片表过滤的 source_type（默认 CifTRONewsItem）")
    parser.add_argument("--upload", action="store_true", help="将查询结果按 tro_post schema 上传到 Sanity")
    parser.add_argument("--dry_run", action="store_true", help="与 --upload 同用，仅打印将要上传的内容，不请求 Sanity")
    parser.add_argument("--sanity_project_id", required=False, help="Sanity 项目 ID，可通过环境变量 SANITY_PROJECT_ID 传递")
    parser.add_argument("--sanity_dataset", default="production", help="Sanity 数据集，可通过环境变量 SANITY_DATASET 传递")
    parser.add_argument("--sanity_token", required=False, help="Sanity 写权限 Token，可通过环境变量 SANITY_TOKEN 传递")
    args = parser.parse_args()

    token = args.cf_d1_api_token or os.getenv("CF_D1_API_TOKEN")
    account_id = args.cf_d1_account_id or os.getenv("CF_D1_ACCOUNT_ID")
    database_id = args.cf_d1_database_id or os.getenv("CF_D1_DATABASE_ID")
    sanity_project = args.sanity_project_id or os.getenv("SANITY_PROJECT_ID")
    sanity_dataset = args.sanity_dataset or os.getenv("SANITY_DATASET") or "production"
    sanity_token = args.sanity_token or os.getenv("SANITY_TOKEN")

    if not all([token, account_id, database_id]):
        print("缺少 D1 配置，请提供 --cf_d1_* 或环境变量 CF_D1_API_TOKEN / CF_D1_ACCOUNT_ID / CF_D1_DATABASE_ID")
        return

    from cloudflare import Cloudflare
    client = Cloudflare(api_token=token)
    rows = run_select_join(client, account_id, database_id, args.source_type)
    print(f"共 {len(rows)} 条")
    for i, row in enumerate(rows[:5]):
        print(f"  [{i+1}] id={row.get('id')}, origin_article_id={row.get('origin_article_id')}, extract_case_number={row.get('extract_case_number')}")
    if len(rows) > 5:
        print(f"  ... 其余 {len(rows) - 5} 条")
    if args.upload and rows:
        if not sanity_project or not sanity_token:
            print("上传 Sanity 需要 --sanity_project_id 与 --sanity_token（或环境变量 SANITY_PROJECT_ID / SANITY_TOKEN）")
            return rows
        print("上传到 Sanity (tro_post)...")
        create_sanity_doc(rows, sanity_project, sanity_dataset, sanity_token, dry_run=args.dry_run)
    return rows


if __name__ == "__main__":
    main()
