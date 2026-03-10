import re
def clean_edges(text):
    # 正则逻辑：
    # ^[^a-zA-Z0-9]+  -> 匹配开头所有“非字母、非数字”的字符
    # |               -> 或
    # [^a-zA-Z0-9]+$  -> 匹配结尾所有“非字母、非数字”的字符
    # pattern = r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$"
    """
    仅去除首尾非字母非数字字符，保留中间的所有字符（含空格、中文等）。
    """
    # 1. ^[^a-zA-Z0-9]+ 匹配开头所有非字母非数字
    # 2. |              或者
    # 3. [^a-zA-Z0-9]+$ 匹配结尾所有非字母非数字
    # return re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", text)
    return re.sub(r"^[^\u4e00-\u9fa5a-zA-Z0-9]+|[^\u4e00-\u9fa5a-zA-Z0-9]+$", "", text)
    
    # 将匹配到的部分替换为空字符串
    return re.sub(pattern, "", text)

# --- 测试用例 ---
test_cases = [
    "!!!Hello World 123***",
    "---2026-03-06---",
    "  #Python@  ",
    "123abc456",
    "：Western District of Pennsylvania",
    "2026年03月06日"
]

for t in test_cases:
    print(f"原字符: '{t}' -> 处理后: '{clean_edges(t)}'")