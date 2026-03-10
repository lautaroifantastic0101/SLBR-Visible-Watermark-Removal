import pandas as pd

import pandas as pd
from rapidfuzz import process, utils

from src.utils.parse_utils import extract_urls



"""配置文件处理

Returns:
    _type_: _description_
"""

class BrandManager:
    def __init__(self, excel_path):
        # 1. 加载 Excel 并转换为字典
        df = pd.read_excel(excel_path)

        # 若 brand 列包含 "||"，按 "||" 拆成多行，其余列复制
        def split_brand(s):
            if pd.isna(s):
                return []
            s = str(s).strip()
            if "||" not in s:
                return [s] if s else []
            return [p.strip() for p in s.split("||") if p.strip()]

        df["_brand_split"] = df["brand"].apply(split_brand)
        df = df.explode("_brand_split", ignore_index=True).drop(columns=["brand"]).rename(columns={"_brand_split": "brand"})
        df = df[df["brand"].astype(str).str.len() > 0]  # 去掉空 brand 行

        # NaN 统一为空字符串，避免 config 中出现 nan
        df = df.fillna("")

        # 结构：{ 'BrandName': {'brand_website': '...', 'brand_info': '...'} }
        self.config = df.set_index('brand').to_dict(orient='index')
        # 提取所有的 key 用于匹配
        self.brand_list = list(self.config.keys())

    def find_brand(self, query, score_cutoff=90):
        """
        模糊查询品牌信息
        :param query: 用户输入的字符串
        :param score_cutoff: 相似度阈值 (0-100)，低于此分数忽略
        :return: (匹配到的品牌名, 详细数据, 匹配分数)
        """
        if not query:
            return None

        # 2. 使用 rapidfuzz 进行提取
        # processor=utils.default_process 会自动处理大小写、空格和特殊字符
        # print(self.brand_list)
        result = process.extractOne(
            query, 
            self.brand_list, 
            processor=utils.default_process,
            score_cutoff=score_cutoff
        )

        if result:
            matched_name, score, index = result
            return {
                "brand": matched_name,
                "data": self.config[matched_name],
                "score": score
            }
        return None



def _most_complete_str(*values):
    """从多个字符串中取最完整的（非空且更长优先）。"""
    def norm(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        return str(v).strip()
    candidates = [norm(v) for v in values]
    non_empty = [s for s in candidates if s]
    if not non_empty:
        return candidates[0] if candidates else ""
    return max(non_empty, key=len)


def refine_brand_config_xlsx(input_path: str, output_path: str) -> None:
    """
    根据 input 中的 brand_website/brand_web2、brand_info/brand_info2 合并出最完整的
    brand_website 和 brand_info，写出到 output。

    Input 列：brand, brand_ch_name, brand_type, brand_website, brand_info,
             brand_info_length, brand_web2, brand_info2
    Output 列：brand, brand_ch_name, brand_type, brand_website, brand_info
    """
    df = pd.read_excel(input_path)
    df = df.fillna("")

    rows = []
    for _, row in df.iterrows():
        brand = row.get("brand", "")
        brand_ch_name = row.get("brand_ch_name", "")
        brand_type = row.get("brand_type", "")
        brand_website = _most_complete_str(row.get("brand_website"), row.get("brand_web2"))
        brand_info = _most_complete_str(row.get("brand_info"), row.get("brand_info2"))
        rows.append({
            "brand": brand,
            "brand_ch_name": brand_ch_name,
            "brand_type": brand_type,
            "brand_website": brand_website,
            "brand_info": brand_info,
        })
    out_df = pd.DataFrame(rows)
    out_df.to_excel(output_path, index=False)

def refine_brand_config_xlsx_same(input_path: str, output_path: str) -> None:
    df = pd.read_excel(input_path)
    df = df.fillna("")


    rows = []
    for _, row in df.iterrows():
        brand = row.get("brand", "")
        brand_ch_name = row.get("brand_ch_name", "")
        brand_type = row.get("brand_type", "")
        brand_website = _most_complete_str(row.get("brand_website"), row.get("brand_web"))
        brand_info = row.get("brand_info")
        rows.append({
            "brand": brand,
            "brand_ch_name": brand_ch_name,
            "brand_type": brand_type,
            "brand_website": brand_website,
            "brand_info": brand_info,
        })
        
        if len(brand_website) <= 3:
            urls = extract_urls(brand_info)
            if len(urls) > 0:
                print(urls, brand_info)
            
    out_df = pd.DataFrame(rows)





if __name__ == '__main__':
    # --- 使用示例 ---
    # 假设 Excel 文件名为 'brands.xlsx'
    # manager = BrandManager('config/brand_info_config.xlsx')

    # # 模拟用户输入，比如拼写错误的 "Niki" 或大小写不一的 "apple inc"
    # user_input = "Roku"
    # match_result = manager.find_brand(user_input)
    # print(match_result)

    # if match_result:
    #     print(f"🎯 匹配成功！")
    #     print(f"输入: {user_input} -> 匹配到: {match_result['brand']} (可靠度: {match_result['score']}%)")
    #     print(match_result['data'])
    #     print(f"网址: {match_result['data']['brand_website']}")
    #     print(f"简介: {match_result['data']['brand_info']}")
    # else:
    #     print("❌ 未找到匹配的品牌，请检查输入。")
    refine_brand_config_xlsx_same('/Users/wushan/Desktop/brand_info_config_raw.xlsx', '/Users/wushan/Downloads/test_config.xlsx')

