import pandas as pd

import pandas as pd
from rapidfuzz import process, utils

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




if __name__ == '__main__':
    # --- 使用示例 ---
    # 假设 Excel 文件名为 'brands.xlsx'
    manager = BrandManager('config/brand_info_config.xlsx')

    # 模拟用户输入，比如拼写错误的 "Niki" 或大小写不一的 "apple inc"
    user_input = "Fear of God"
    match_result = manager.find_brand(user_input)
    print(match_result)

    if match_result:
        print(f"🎯 匹配成功！")
        print(f"输入: {user_input} -> 匹配到: {match_result['brand']} (可靠度: {match_result['score']}%)")
        print(match_result['data'])
        print(f"网址: {match_result['data']['brand_website']}")
        print(f"简介: {match_result['data']['brand_info']}")
    else:
        print("❌ 未找到匹配的品牌，请检查输入。")
