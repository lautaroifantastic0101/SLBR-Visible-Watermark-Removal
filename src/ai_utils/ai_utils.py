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
    


if __name__ == "__main__":
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    auth_token = os.environ.get("CF_AI_TOKEN", "")

    # prompt = "ALBION BRAND FOUNDRY LTD 概括介绍；100个字以内（中文）；"
    # prompt = "返回Crye Precision LLC  official website"
    model = '@cf/meta/llama-3-8b-instruct'
    # clean_prompt = remove_sensitive_segments(prompt)
    # print(clean_prompt)
    clean_prompt = ''

    result = call_llama(account_id, auth_token, model, clean_prompt)
    print(result)
