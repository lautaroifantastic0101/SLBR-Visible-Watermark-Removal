import argparse
import os

import requests


DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"


def call_deepseek_chat(api_key, prompt, system_content, model=DEFAULT_MODEL, timeout=60):
	"""Call DeepSeek chat completions API and return the parsed JSON payload."""
	if not api_key:
		raise ValueError("DeepSeek API key is required")
	if not prompt or not prompt.strip():
		raise ValueError("Prompt must not be empty")

	response = requests.post(
		DEEPSEEK_API_URL,
		headers={
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json",
		},
		json={
			"model": model,
			"messages": [
				{"role": "system", "content": system_content},
				{"role": "user", "content": prompt},
			],
			"stream": False,
		},
		timeout=timeout,
	)
	response.raise_for_status()
	return response.json()


def parse_deepseek_response(response):
	"""Extract content and metadata from a DeepSeek chat completions response."""
	if not isinstance(response, dict):
		return {"content": "", "model": None, "usage": None}

	choices = response.get("choices") or []
	message = choices[0].get("message", {}) if choices else {}
	return {
		"content": (message.get("content") or "").strip(),
		"model": response.get("model"),
		"usage": response.get("usage") if isinstance(response.get("usage"), dict) else None,
	}


def translate_english_to_chinese(text, api_key=None, model=DEFAULT_MODEL):
	"""Translate English input into concise natural Chinese with DeepSeek."""
	if not text or not text.strip():
		return ""

	resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
	system_content = (
		"You are a professional translation assistant. "
		"Translate the user's English text into fluent Simplified Chinese only. "
		"Preserve the original meaning, tone, formatting, and proper nouns when appropriate. "
		"Do not add explanations or commentary."
	)
	prompt = f"Translate the following English text into Simplified Chinese:\n\n{text.strip()}"
	response = call_deepseek_chat(
		api_key=resolved_api_key,
		prompt=prompt,
		system_content=system_content,
		model=model,
	)
	parsed = parse_deepseek_response(response)
	return parsed["content"]


def parse_args():
	parser = argparse.ArgumentParser(description="Translate English text to Simplified Chinese with DeepSeek API.")
	parser.add_argument("text", nargs="?", default="", help="English text to translate.")
	parser.add_argument("--api_key", dest="api_key", default=None, help="DeepSeek API key. Defaults to DEEPSEEK_API_KEY.")
	parser.add_argument("--model", default=DEFAULT_MODEL, help="DeepSeek model name. Defaults to deepseek-v4-flash.")
	return parser.parse_args()


def main(text, api_key=None, model=DEFAULT_MODEL):
	translated = translate_english_to_chinese(text=text, api_key=api_key, model=model)
	print(translated)


if __name__ == "__main__":
	args = parse_args()
	main(text=args.text, api_key=args.api_key, model=args.model)
