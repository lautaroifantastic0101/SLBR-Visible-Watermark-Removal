import json
import re
from typing import Any

from numpy import isin

_brand_manager = None

def _get_brand_manager():
    global _brand_manager
    if _brand_manager is None:
        from src.utils.config_utils import BrandManager
        _brand_manager = BrandManager("config/brand_info_config.xlsx")
    return _brand_manager


def remove_sensitive_segments(text: str, sensitive_words: tuple | list = ("赛贝","雨果" ,"麦小天")) -> str:
    """
    按中文逗号、句号分句，去掉包含敏感词的短句，再用原始标点拼接回去。

    Args:
        text: 原始文本
        sensitive_words: 敏感词集合，默认 ("赛贝",)。某短句包含任一敏感词则整句删除。

    Returns:
        删除含敏感词短句后用原标点合并的文本
    """
    if not text or not isinstance(text, str):
        return text or ""
    parts = re.split(r"([，。])", text)
    segments = parts[0::2]
    delimiters = parts[1::2]
    out = []
    for i, seg in enumerate(segments):
        if any(w in seg for w in sensitive_words):
            continue
        out.append(seg)
        if i < len(delimiters):
            out.append(delimiters[i])
    return "".join(out)


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
        raw = raw.replace('\n', '')
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



def clean_edges(text):
    # 正则逻辑：
    # ^[^a-zA-Z0-9]+  -> 匹配开头所有“非字母、非数字”的字符
    # |               -> 或
    # [^a-zA-Z0-9]+$  -> 匹配结尾所有“非字母、非数字”的字符
    pattern = r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$"
    
    # 将匹配到的部分替换为空字符串
    return re.sub(pattern, "", text)

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


# 版权登记号格式：VA 2-467-346、PA 1-234-567 等（美国版权局）
_COPYRIGHT_PATTERN = re.compile(r"^(?:VA|PA|SR|TX)\s*\d+-\d+-\d+$", re.IGNORECASE)


def is_copyright_number(s: str) -> bool:
    """
    判断单个字符串是否为版权登记号（如 VA 2-467-346），否则视为专利号。

    Args:
        s: 待判断的字符串（可能为专利号或版权号）

    Returns:
        True 表示版权号，False 表示专利号
    """
    if not s or not isinstance(s, str):
        return False
    return bool(_COPYRIGHT_PATTERN.match(str(s).strip()))


def extract_copyright_numbers(text: str, unique: bool = True) -> list[str]:
    """
    从文本中提取版权登记号，格式如 VA 2-467-346、VA 2-465-678（美国版权局 VA/PA/SR/TX 等）。

    Args:
        text: 原始文本
        unique: 是否去重，默认 True

    Returns:
        匹配到的版权号列表，如 ["VA 2-467-346", "VA 2-465-678"]
    """
    if not text or not isinstance(text, str):
        return []
    # VA/PA/SR/TX 等前缀 + 空格 + 数字-数字-数字
    pattern = r"(?:VA|PA|SR|TX)\s*\d+-\d+-\d+"
    found = re.findall(pattern, text, re.IGNORECASE)
    # 统一为 "VA 2-467-346" 形式（前缀后保留一个空格）
    normalized = []
    for s in found:
        s = s.strip()
        if re.match(r"^[A-Za-z]+\s*", s):
            s = re.sub(r"^([A-Za-z]+)\s*", lambda m: m.group(1).upper() + " ", s, count=1)
        normalized.append(s)
    if unique:
        return list(dict.fromkeys(normalized))
    return normalized


def extract_urls(text):
    """
    这个正则可以匹配大多数以 http 或 https 开头的链接

    Args:
        text (_type_): _description_

    Returns:
        _type_: _description_
    """
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    urls = re.findall(url_pattern, text)
    if urls is None:
        return []
    return urls

def _str_ob(ob):
    if ob is None:
        return "" 
    elif isinstance(ob, str):
        return ob.replace("'", "`")
    elif isinstance(ob, list):
        return json.dumps(ob).replace("'", "`")
    elif isinstance(ob, dict):
        ret = ''
        for k, v in ob.items():
            ret = ret + f"{k}: {v};"
        return ret.replace("'", "`")


def to_str_ob(ob):
    if ob is None:
        return "" 
    elif isinstance(ob, str):
        return ob.replace("'", "`")
    elif isinstance(ob, list):
        return json.dumps(ob).replace("'", "`")
    elif isinstance(ob, dict):
        ret = ''
        for k, v in ob.items():
            ret = ret + f"{k}: {v};"
        return ret.replace("'", "`")
            
            
        

def extract_brand_name(gemini_ai_resp):
    """从ai返回结果中，解析出来品牌和品牌的信息
    因为采取的sql都是单引号，所以会在brand和brand_info文本中作去除单引号的处理

    Args:
        gemini_ai_resp (_type_): _description_

    Returns:
        _type_: _description_
    """
    if not gemini_ai_resp or not isinstance(gemini_ai_resp, str):
        return '', '', ''
    try:
        gemini_ai_resp_json = parse_json_text(gemini_ai_resp)
        if isinstance(gemini_ai_resp_json, list):
            return '', '', ''
        if gemini_ai_resp_json is None:
            return '', '', ''
        else:
            brand_name = _str_ob(gemini_ai_resp_json.get("品牌方"))

            brand_info = _str_ob(gemini_ai_resp_json.get("品牌方信息"))
            url = ''
            urls = []
            if brand_info is not None:
                urls = list(set(extract_urls(brand_info)))
            if len(urls) > 0:
                url = urls[0]

            # brand_name 非空时，优先从 config 获取 brand_info 和 brand_website
            if brand_name and str(brand_name).strip():
                try:
                    manager = _get_brand_manager()
                    match = manager.find_brand(brand_name.strip())

                    if match and match.get("data"):
                        match_brand = match['brand']
                        match_score = match['score']
                        if match_score > 80:
                            brand_name = match_brand
                        data = match["data"]
                        if data.get("brand_info"):
                            brand_info = data["brand_info"]
                        if data.get("brand_website"):
                            url = data["brand_website"]
                except Exception as e:
                    print(f"config_utils find_brand 失败 [{brand_name}]: {e}")

            return brand_name, brand_info, url
    except Exception as e:
        print(f"error: {e} . {gemini_ai_resp}")
        return '', '', ''



# 维权类型原始值 -> 标准化为：商标维权、专利维权、版权维权
LAW_TYPE_STANDARD = ("商标维权", "专利维权", "版权维权")


def _normalize_law_type(raw_cp) -> str:
    """
    将 raw_cp 标准化为 商标维权、专利维权、版权维权 三类（可多选，逗号分隔）。
    可能输入：专利维权,版权维权,商标维权,版权,TRO临时禁令,商标和专利维权,TRO维权,IP维权,
    全方位维权,商标及版权维权,知识产权维权,TRO,专利,肖像图维权,商标和版权,商标,商标、版权,
    知识产权纠纷,TRO 维权,商标及版权 等。
    """
    if raw_cp is not None and isinstance(raw_cp, list):
        raw_cp =  ','.join(raw_cp)
    if raw_cp is None or not isinstance(raw_cp, str):
        return ""
    s = raw_cp.strip()
    if not s:
        return ""
    parts = []
    if "商标" in s:
        parts.append("商标维权")
    if "专利" in s:
        parts.append("专利维权")
    if "版权" in s or "肖像" in s:
        parts.append("版权维权")

    # 未命中上述关键词时，TRO/IP/全方位/知识产权 等视为涵盖多类，返回全部三类
    if not parts:
        if any(k in s for k in ("TRO", "IP", "全方位", "知识产权", "维权")):
            return "商标维权,专利维权,版权维权"
        return ""
    if len(parts) == 0:
        parts.append("侵权")
    return ",".join(dict.fromkeys(parts))


def extract_law_type_info(gemini_ai_resp):
    """从信息中提取案件的维权类型，并标准化为：商标维权、专利维权、版权维权。"""
    ret = ""
    if not gemini_ai_resp or not isinstance(gemini_ai_resp, str):
        return None

    gemini_ai_resp_json = parse_json_text(gemini_ai_resp)
    if gemini_ai_resp_json and isinstance(gemini_ai_resp_json, dict):
        raw_cp = gemini_ai_resp_json.get("维权类型") or gemini_ai_resp_json.get("type_of_case") or gemini_ai_resp_json.get("rights_type")
        ret = _normalize_law_type(raw_cp)
    return ret
 