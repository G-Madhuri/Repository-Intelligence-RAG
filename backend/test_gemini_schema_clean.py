import os
import json
from dotenv import load_dotenv

load_dotenv()

from services.llmAnalyzer import AnalysisResponse

def clean_gemini_schema(schema):
    if isinstance(schema, dict):
        cleaned = {}
        for key, value in schema.items():
            if key == "additionalProperties":
                continue
            cleaned[key] = clean_gemini_schema(value)
        return cleaned
    elif isinstance(schema, list):
        return [clean_gemini_schema(item) for item in schema]
    return schema

raw_schema = AnalysisResponse.model_json_schema()
print(f"Raw schema contains 'additionalProperties': {'additionalProperties' in json.dumps(raw_schema)}")

cleaned = clean_gemini_schema(raw_schema)
print(f"Cleaned schema contains 'additionalProperties': {'additionalProperties' in json.dumps(cleaned)}")

api_key = os.getenv("GEMINI_API_KEY")
if api_key and not api_key.startswith("AQ."):
    from google import genai
    client = genai.Client(api_key=api_key)
    print("Testing Gemini generate_content with cleaned response_schema...")
    try:
        res = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Return a minimal mock repository intelligence response.",
            config={
                'response_mime_type': 'application/json',
                'response_schema': cleaned,
                'temperature': 0.2
            }
        )
        print("[+] Success! Gemini accepted cleaned response_schema!")
    except Exception as e:
        print(f"[!] Error: {e}")
