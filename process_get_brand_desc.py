
import os

import pandas as pd
from datetime import datetime

from src.ai_utils.ai_utils import get_brand_desc, get_brand_website 

"""_summary_
输入：brands
输出：
调用ai模型，返回品牌介绍和官网地址

最后写入到excel中：brand, brand_desc, brand_website
"""

if __name__ == '__main__':
    brands = [
'Epicord',
'Fengxian Chendian Electronic Commerce Co., Ltd.',
'Fox Head, Inc.',
'GS Holistic, LLC',
'Grill Scraper',
'Guangdongsheng Shunhechuanmei Co., Ltd',
'G型无线充电氛围灯',
'HUANGJI YANG',
'Hangzhou Yuanzu Technology Co., Ltd',
'Hari Studios',
'Harry Styles',
'ICON WORLDWIDE PTY LTD',
'Iconic NKC IP LLC',
'Ina Tomecek',
'Ink & Rags LLC',
'JTLE INVESTMENTS LLC',
'Karsten Manufacturing Corporation',
'Kuiper Ventures LLC',
'Kyndred Spirit, LLC',
'LOUIS POULSEN',
'LOVITEDO, LLC',
'LeChong Maoyi Xiantao Youxiangongsi',
'Legend Pictures, LLC',
'Little ELF Products.INC',
'Living Active, LLC',
'Lovitedo LLC',
'MARATAC, INC',
'MOB ENTERTAINMENT, INC.',
'Melissa Bamberg',
'Metzfab Industries, LLC et al',
'Michelle E. De Sousa&nbsp;Jose De Jesus De Sousa',
'Microjig',
'NEWAGE SUPPLY, INC.',
'NIKE, Inc.',
'ORLY FIDELMAN',
'PICKULS GIZMO LTD',
'PUFFIN COOLERS, LLC',
'Popilush, LLC',
'Popsockets LLC',
'QUANZHOU***LTD',
'Ride-on Luaggage',
'Roku, Inc.',
'Royer Brands International S.A.R.L.',
'Rubie’s Costume Company',
'SHUANGXI ZHANG',
'Safeworld International',
'SheFit Operating Company, LLC',
'Shenzhen Kunshengze Electronic Commerce Co., Ltd.',
'Shenzhen Saikenxin',
'Simply Mossy Art',
'Sport Dimension, Inc',
'Stanislav Yurievich Osipov',
'Stanley',
'Sterling International Inc.',
'Stewart Creative, Llc',
'Superhype Tapes, Ltd.',
'THE KRAK’IN',
'THE SMILEY COMPANY SPRL',
'THOMAS WOOD',
'TIFFANY (NJ) LLC',
'Thousand Oaks Barrel Co. LLC',
'Tory Burch',
'VOLOOM',
'Victoria’s Secret & Co.',
'WARNER BROS. ENTERTAINMENT INC',
'Weirdwatercolours Ltd.',
'XAVORK WOOLIAND INC.',
'YIPU（TIANJIN）INTELLIGENT TECHNOLOGY CO.，LTD',
'Yoeu Inc.',
    ]
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    auth_token = os.environ.get("CF_AI_TOKEN", "")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_excel = f'/Users/wushan/Downloads/brand_website_{ts}.xlsx'

    rows = []
    brand_desc = ""
    brand_website = ""
    for brand in brands:
        try:
            brand_desc = get_brand_desc(account_id, auth_token, brand)
            brand_website = get_brand_website(account_id, auth_token, brand)
            print(f"{brand}||{brand_website}")
        except Exception as e:
            print(f"错误 brand={brand}: {e}")
            brand_website = ""
        rows.append({"brand": brand, "brand_desc": brand_desc, "brand_website": brand_website})

    df = pd.DataFrame(rows)
    df.to_excel(output_excel, index=False)
    print(f"已写入 {output_excel}，共 {len(rows)} 条")
    