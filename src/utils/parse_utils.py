import json
import re

from numpy import isin

# -----------------------------------------------------------------------------
# 从文本中提取并解析 JSON
# -----------------------------------------------------------------------------


def parse_json_text(text: str):
    """
    从文本中提取 JSON 并解析为 Python 对象。
    支持：
    1) 纯 JSON 字符串
    2) Markdown 代码块内的 JSON（```json ... ``` 或 ``` ... ```）
    3) 正文中内嵌的 JSON（从第一个 [ 或 { 起括号匹配截取）
    输入样例见 tmp/json_sample1.json, json_sampel2.json, json_sample3.json
    """
    if text is None:
        return None
    if not isinstance(text, str):
        return None
    s = text.strip()
    if not s:
        return None

    # 1) 整体尝试解析
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2) 提取 ```json ... ``` 或 ``` ... ``` 中的内容
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
    if m:
        raw = m.group(1).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    # 3) 从第一个 [ 或 { 开始括号匹配截取 JSON 子串
    start_arr = s.find("[")
    start_obj = s.find("{")
    start = -1
    open_char = None
    close_char = None
    if start_arr >= 0 and (start_obj < 0 or start_arr < start_obj):
        start = start_arr
        open_char, close_char = "[", "]"
    elif start_obj >= 0:
        start = start_obj
        open_char, close_char = "{", "}"

    if start >= 0:
        depth = 0
        i = start
        while i < len(s):
            if s[i] == open_char:
                depth += 1
            elif s[i] == close_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[start : i + 1])
                    except json.JSONDecodeError:
                        break
            elif s[i] in ('"', "'"):
                # 跳过字符串，避免括号在字符串内被误计
                quote = s[i]
                i += 1
                while i < len(s):
                    if s[i] == "\\":
                        i += 2
                        continue
                    if s[i] == quote:
                        break
                    i += 1
            i += 1

    return None


# -----------------------------------------------------------------------------
# 专利号提取
# -----------------------------------------------------------------------------

# 常见专利号格式（国家/类型前缀 + 数字）
# US: 8,123,456 / US8123456；设计 D123456、USD974030S1；植物 PP12345；再颁 RE12345
# CN: CN123456789.0 / CN 202010123456.X；长数字号 90080187090004
# EP: EP 1234567 A1；WO/PCT: WO 2020/123456；JP: JP 2020-123456
PATENT_NUMBER_PATTERN = re.compile(
    r"\b("
    r"(?:US|CN|EP|WO|PCT|JP|KR|DE|GB)\s*[\d,\.\-/]+(?:\s*[A-Z]\d?)?"
    r"|USD\d+S\d+"
    r"|(?:US\s*)?(?:D|PP|RE)\s*\d[\d,]*"
    r"|\d{1,3}(?:,\d{3})+\s*(?:\.\d+)?(?:\s*[A-Z]\d?)?"
    r"|\d{12,}"
    r")\b",
    re.IGNORECASE,
)


def extract_patent_numbers(text: str, unique: bool = True):
    """
    从文本中提取专利号，返回匹配到的字符串列表。
    支持常见格式：US/CN/EP/WO/PCT/JP 等国家代码+数字、美国 D/PP/RE 类型、USD974030S1、纯数字带逗号、12 位以上长数字（如 90080187090004）等。
    :param text: 输入文本
    :param unique: 是否去重（保持出现顺序），默认 True
    :return: 专利号字符串列表，无匹配返回 []
    """
    if not text or not isinstance(text, str):
        return []
    matches = PATENT_NUMBER_PATTERN.findall(text)
    # 去掉仅逗号/点的无效串，并 strip
    cleaned = []
    for m in matches:
        s = m.strip()
        if len(s) >= 2 and not all(c in ".,\t " for c in s):
            cleaned.append(s)
    if unique:
        return list(dict.fromkeys(cleaned))
    return cleaned


# -----------------------------------------------------------------------------
# 美国州：中文常见译名 -> 英文名；用于从法院名称等字符串中提取州
# -----------------------------------------------------------------------------
US_STATE_ZH_TO_EN = {
    "伊利诺伊": "Illinois",
    "加利福尼亚": "California",
    "加州": "California",
    "纽约": "New York",
    "德克萨斯": "Texas",
    "德州": "Texas",
    "佛罗里达": "Florida",
    "佛州": "Florida",
    "华盛顿": "Washington",
    "俄亥俄": "Ohio",
    "宾夕法尼亚": "Pennsylvania",
    "宾州": "Pennsylvania",
    "乔治亚": "Georgia",
    "佐治亚": "Georgia",
    "北卡罗来纳": "North Carolina",
    "北卡": "North Carolina",
    "密歇根": "Michigan",
    "密西根": "Michigan",
    "新泽西": "New Jersey",
    "弗吉尼亚": "Virginia",
    "维吉尼亚": "Virginia",
    "马萨诸塞": "Massachusetts",
    "麻省": "Massachusetts",
    "亚利桑那": "Arizona",
    "田纳西": "Tennessee",
    "印第安纳": "Indiana",
    "密苏里": "Missouri",
    "马里兰": "Maryland",
    "威斯康星": "Wisconsin",
    "科罗拉多": "Colorado",
    "明尼苏达": "Minnesota",
    "南卡罗来纳": "South Carolina",
    "南卡": "South Carolina",
    "阿拉巴马": "Alabama",
    "路易斯安那": "Louisiana",
    "肯塔基": "Kentucky",
    "俄勒冈": "Oregon",
    "俄克拉荷马": "Oklahoma",
    "康涅狄格": "Connecticut",
    "内华达": "Nevada",
    "犹他": "Utah",
    "爱荷华": "Iowa",
    "阿肯色": "Arkansas",
    "密西西比": "Mississippi",
    "堪萨斯": "Kansas",
    "新墨西哥": "New Mexico",
    "内布拉斯加": "Nebraska",
    "西弗吉尼亚": "West Virginia",
    "爱达荷": "Idaho",
    "夏威夷": "Hawaii",
    "新罕布什尔": "New Hampshire",
    "缅因": "Maine",
    "蒙大拿": "Montana",
    "罗德岛": "Rhode Island",
    "特拉华": "Delaware",
    "南达科他": "South Dakota",
    "北达科他": "North Dakota",
    "阿拉斯加": "Alaska",
    "佛蒙特": "Vermont",
    "怀俄明": "Wyoming",
    "哥伦比亚特区": "District of Columbia",
    "华盛顿特区": "District of Columbia",
}

# 英文州名列表，用于在字符串中匹配（按长度降序，优先匹配长名如 New York）
US_STATE_NAMES = [
    "District of Columbia", "North Carolina", "South Carolina", "New Hampshire",
    "Rhode Island", "New Jersey", "New Mexico", "New York", "West Virginia",
    "Massachusetts", "Pennsylvania", "Connecticut", "Washington", "California",
    "Minnesota", "Tennessee", "Wisconsin", "Louisiana", "Maryland", "Kentucky",
    "Colorado", "Oklahoma", "Virginia", "Mississippi", "Arkansas", "Kansas",
    "Nebraska", "Illinois", "Michigan", "Georgia", "Hawaii", "Florida",
    "Delaware", "Montana", "Vermont", "Wyoming", "Alabama", "Indiana",
    "Missouri", "Arizona", "Oregon", "Iowa", "Utah", "Nevada", "Alaska",
    "Texas", "Ohio", "Maine", "Idaho", "North Dakota", "South Dakota",
]

# 英文名 -> 中文名（取较长中文，如 加利福尼亚 优先于 加州）
US_STATE_EN_TO_ZH = {}
for zh, en in US_STATE_ZH_TO_EN.items():
    if en not in US_STATE_EN_TO_ZH or len(zh) > len(US_STATE_EN_TO_ZH[en]):
        US_STATE_EN_TO_ZH[en] = zh

# 两字母缩写 -> 英文名（USPS）
US_STATE_ABBR_TO_EN = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def extract_us_state(text: str):
    """从字符串中提取美国州信息，返回中文州名。支持中文法院名（如 伊利诺伊州北区法院）和英文（如 Northern District of Illinois）。"""
    if not text or not isinstance(text, str):
        return None
    s = text.strip()
    if not s:
        return None
    # 1) 中文：按 US_STATE_ZH_TO_EN 匹配，直接返回匹配到的中文
    for zh, en in US_STATE_ZH_TO_EN.items():
        if zh in s:
            return zh
    # 2) 英文：在字符串中查找州名，再转为中文
    s_lower = s.lower()
    for name in US_STATE_NAMES:
        if name.lower() in s_lower:
            return US_STATE_EN_TO_ZH.get(name)
    # 3) 两字母缩写：匹配后转为中文
    abbr = re.search(
        r"\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b",
        s,
        re.IGNORECASE,
    )
    if abbr:
        en = US_STATE_ABBR_TO_EN.get(abbr.group(1).upper())
        return US_STATE_EN_TO_ZH.get(en) if en else None
    return None



# import json
# def parse_json_text(s: str):
#     if '```' in s:
#         """解析可能是纯 JSON 或 ```json ... ``` 包裹的字符串。"""
#         if not s or not isinstance(s, str):
#             return None
#         s = s.strip()
#         try:
#             return json.loads(s)
#         except json.JSONDecodeError:
#             pass
#         m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
#         if m:
#             try:
#                 return json.loads(m.group(1).strip())
#             except json.JSONDecodeError:
#                 pass
#         return None
#     else:
#         """提取所有 {{ ... }} 之间的文本（贪婪模式）"""
#         if not text or not isinstance(text, str):
#         return []
#         pattern = r"\{\{(.*)\}\}"
#     matches = re.findall(pattern, text, re.DOTALL)
#     return matches



    
def is_gemini_ai_resp_array(gemini_ai_resp) -> bool:
    """判断 gemini_ai_resp 是否为数组。"""
    if not gemini_ai_resp or not isinstance(gemini_ai_resp, str):
        return False
    try:
        gemini_ai_resp_json = parse_json_text(gemini_ai_resp)
        # gemini_ai_resp_json = json.loads(gemini_ai_resp)
        return isinstance(gemini_ai_resp_json, list)
    except Exception as e:
        print(f"error: {e} . {gemini_ai_resp}")
        return False


def extract_brand_name(gemini_ai_resp):
    """从ai返回结果中，解析出来品牌和品牌的信息

    Args:
        gemini_ai_resp (_type_): _description_

    Returns:
        _type_: _description_
    """
    if not gemini_ai_resp or not isinstance(gemini_ai_resp, str):
        return None, None
    try:
        gemini_ai_resp_json = parse_json_text(gemini_ai_resp)
        if isinstance(gemini_ai_resp_json, list):
            return None, None
        if gemini_ai_resp_json is None:
            return None, None
        else:
            print(type(gemini_ai_resp_json.get("品牌方信息")))
            return gemini_ai_resp_json.get("品牌方"), gemini_ai_resp_json.get("品牌方信息")
    except Exception as e:
        print(f"error: {e} . {gemini_ai_resp}")
        return None, None


