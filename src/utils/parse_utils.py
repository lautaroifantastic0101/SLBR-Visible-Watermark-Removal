import re
# 美国州：中文常见译名 -> 英文名；用于从法院名称等字符串中提取州
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

