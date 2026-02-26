import json
import sqlite3
from tro_crawl_item_to_sanity_tro_post_doc import row_to_tro_post_doc

case_number = '2025-cv-04767'
filter = '(' + ','.join([f'\'{i}\'' for i in case_number.split(',')]) + ')'
print(filter)
sql = f"""
    SELECT
    a.id,
    a.gemini_ai_resp,
    a.patent_arr,
    a.title,
    a.case_number_arr,
    a.extract_case_number,
    a.source_type,
    a.brand,
    a.brand_info,
    a.brand_website,
    b.crawl_item AS basic_info,
    c.crawl_item AS timeline_info,
    d.new_url_arr,
    d.img_type_arr,
    a.violation_type
    FROM (
        select id, 
                origin_article_id,
                gemini_ai_resp, 
                patent_arr, 
                case_number_arr ,
                extract_case_number,
                source_type,
                brand,
                brand_info,
                brand_website,
                violation_type,
                COALESCE(json_extract(crawl_item, '$.title'), '') as title
        FROM tro_crawl_item_tb
        where extract_case_number IN {filter}
        and     source_type in (
        'CifTRONewsItem',
        'MaijiaxingiquTRONewsItem',
        'QqdipTROItem',
        'RuiguanTROItem',
        'ZlvywTROItem'
        )
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
    GROUP BY origin_post_id
    ) d ON a.origin_article_id = d.origin_post_id;
"""

# print(sql)
conn = sqlite3.connect('/Users/wushan/d1cloudflare_db/myblogdatafortest.sqlite3')
cursor = conn.cursor()
results = cursor.execute(sql)
rows = cursor.fetchall()

    # a.id,
    # a.gemini_ai_resp,
    # a.patent_arr,
    # a.title,
    # a.case_number_arr,
    # a.extract_case_number,
    # a.source_type,
    # a.brand,
    # a.brand_info,
    # a.brand_website,
    # b.crawl_item AS basic_info,
    # c.crawl_item AS timeline_info,
    # d.new_url_arr,
    # d.img_type_arr
# 列顺序对应外层 SELECT: id, gemini_ai_resp, patent_arr, title, case_number_arr, extract_case_number, source_type, brand, brand_info, brand_website, basic_info, timeline_info, new_url_arr, img_type_arr
rows = [
    {
        "id": row[0],
        "gemini_ai_resp": row[1] or "",
        "patent_arr": row[2] or "",
        "title": row[3] or "",
        "case_number_arr": row[4] or "",
        "extract_case_number": row[5] or "",
        "source_type": row[6] or "",
        "brand": row[7],
        "brand_info": row[8],
        "brand_website": row[9],
        "case_detail_info": row[10] or "",  # b.crawl_item AS basic_info
        "timeline_info": row[11] or "",
        "new_url_arr": row[12] or "",
        "img_type_arr": row[13] or "",
        "violation_type": row[14] or "",
    }
    for row in rows
]

# print(rows[0])
doc = row_to_tro_post_doc(rows[0])
print(doc)
# print(json.dumps(doc))