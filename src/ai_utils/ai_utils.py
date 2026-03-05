import os
import requests

from src.utils.parse_utils import remove_sensitive_segments, extract_urls

# MODEL = '@cf/qwen/qwen3-30b-a3b-fp8'

# MODEL = '@cf/openai/gpt-oss-120b'


def call_llama(account_id: str, auth_token: str, model, prompt: str, system_content: str = "You are a friendly assistant"):
    """
    调用 Cloudflare Workers AI（Qwen 模型），返回 AI 结果。

    Args:
        account_id: Cloudflare 账号 ID
        auth_token: Cloudflare API Token（需有 AI 权限）
        prompt: 用户输入内容
        system_content: 系统角色说明，默认 "You are a friendly assistant"

    Returns:
        API 返回的 JSON 解析结果（通常含 result.response 等字段）
    """
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def parse_ai_response(response: dict) -> dict:
    """
    解析 Cloudflare Workers AI 返回的 JSON，提取 result.response、success、errors、usage 等。

    入参示例:
        {'result': {'response': '...', 'usage': {...}}, 'success': True, 'errors': [], 'messages': []}

    Returns:
        {
            "response": str,   # AI 回复正文，无则 ""
            "success": bool,
            "errors": list,
            "usage": dict | None,  # prompt_tokens, completion_tokens, total_tokens 等
        }
    """
    if not response or not isinstance(response, dict):
        return {"response": "", "success": False, "errors": [], "usage": None}
    result = response.get("result") or {}
    return {
        "response": (result.get("response") or "").strip(),
        "success": bool(response.get("success")),
        "errors": list(response.get("errors") or []),
        "usage": result.get("usage") if isinstance(result.get("usage"), dict) else None,
    }


def get_brand_desc(account_id, auth_token, brand):
    MODEL = "@cf/meta/llama-3-8b-instruct"
    prompt = f'{brand} 概括介绍；100个字以内（中文）；'
    result = call_llama(account_id, auth_token, MODEL, prompt)
    call_llama(account_id, auth_token, MODEL, prompt)
    parsed = parse_ai_response(result)
    return parsed["response"]
    # print("usage:", parsed["usage"])

def get_brand_website(account_id, auth_token, brand):
    MODEL = "@cf/meta/llama-3-8b-instruct"
    prompt = f'{brand} offical website'
    result = call_llama(account_id, auth_token, MODEL, prompt)
    parsed = parse_ai_response(result)
    urls = extract_urls(parsed["response"] or "")
    return urls[0] if urls else ""
    

def summarise_case(account_id, auth_token, content):
    """调用 AI 模型对 content（如案件内容）进行概括，返回概括文本（中文）。"""
    MODEL = "@cf/meta/llama-3-8b-instruct"
    system_content = "你是一个法律案件摘要助手，请用中文简洁概括给定内容。"
    if len(content) <= 80:
        return remove_sensitive_segments(content)
    prompt = f"请对以下内容进行概括（中文，80字以内）：  {content or ''}"
    clean_prompt = remove_sensitive_segments(prompt)
    result = call_llama(account_id, auth_token, MODEL, clean_prompt, system_content)
    parsed = parse_ai_response(result)

    resp = parsed["response"]
    if "：" in resp:
        return ''.join(resp.split("：")[1:])
    else:
        return resp 

    
if __name__ == "__main__":
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    auth_token = os.environ.get("CF_AI_TOKEN", "")
    print(account_id)
    print(auth_token)

    


    # prompt = "ALBION BRAND FOUNDRY LTD 概括介绍；100个字以内（中文）；"
    # prompt = "返回Crye Precision LLC  official website"
    model = '@cf/meta/llama-3-8b-instruct'
    # clean_prompt = remove_sensitive_segments(prompt)
    # print(clean_prompt)
    content = """
    14张服装产品TRO维权从赛贝TRO案件查询系统获悉，美国纽约服装品牌原告Rumored Inc.于2026年2月9日，发起TRO相关版权侵权诉讼，案件号为26-cv-01475，由Keith律所代理。原告指控多名被告（跨境电商店铺）未经授权，在其运营的在线商店中复制、展示原告享有版权的产品照片，用于销售劣质竞争产品，涉嫌侵犯原告14件服装产品照片的版权。案件信息案件号：26-cv-1475品牌原告：Rumored Inc起诉类型： 版权侵权起诉日期：2026-02-09代理律所：Keith目前案件还未有重大进展，卖家可以在赛贝TRO案件查询系统免费下载诉状和跟进案件最新进度！（公众号菜单及赛贝知识产权官网均有入口）（案件进度，点击图片可放大查看）品牌介绍Rumored Inc.是一家深耕服装、珠宝及配饰领域的美国品牌，总部位于纽约，秉持“东海岸灵魂、全球精神”的品牌定位。该品牌高度重视产品推广的视觉呈现，其用于广告、营销的产品照片均经过精心构图设计，核心目的是向消费者展示产品细节、传递品牌调性，此类照片已成为品牌积累消费者认知、塑造品牌商誉的核心资产。涉案版权本次涉案的14件版权均为原告Rumored Inc.所有，作品类型均为女装产品照片，版权登记生效日期均为2024年11月5日，具体信息如下表所示，赛贝提醒跨境卖家，未经授权不得擅自使用，以免引发侵权风险。产品展示（图片来源：TRO诉状文件；引用日期：2026-02-11）
    """
    # clean_prompt = remove_sensitive_segments(content)
    # result = summarise_case(account_id, auth_token, clean_prompt)

    # # result = call_llama(account_id, auth_token, model, clean_prompt)
    # print(result)
