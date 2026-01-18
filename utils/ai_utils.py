from openai import OpenAI
import json
from ui.api_config import get_api_key

def parse_with_openai(text):
        api_key = get_api_key()
        if not api_key or api_key.strip() in ('0', ''):
            return "Error: API Key not configured. Please go to API Config and enter a valid OpenRouter API key in the Password field."

        try:
            # Use OpenRouter configuration
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            
            prompt = f"""
            Extract invoice details from the text below and return strictly valid JSON.
            Fields:
            - party_name (string)
            - date (YYYY-MM-DD)
            - voucher_no (string)
            - purchase_type (string, guess if not clear)
            - items: list of objects with keys: item_name, tax_category (string), hsn (string), qty (number), unit, list_price (number), discount (number), price (number), amount (number)
            - bill_sundry: list of objects with keys: name, percentage (number), amount (number)

            Text:
            {text[:10000]} 
            """

            response = client.chat.completions.create(
                model="openai/gpt-4o-mini", # OpenRouter model ID
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Output only JSON."},
                    {"role": "user", "content": prompt}
                ],
                # response_format={"type": "json_object"}, # OpenRouter/some providers might not support strict json_object enforcement yet with all models, but gpt-4o-mini usually does. keeping it for now.
                extra_headers={
                    "HTTP-Referer": "https://minib_app.com", # Required by OpenRouter for ranking
                    "X-Title": "MiniB ERP",
                }
            )
            content = response.choices[0].message.content
            # Cleanup code blocks if present (OpenRouter models sometimes return markdown)
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "")
            elif content.startswith("```"):
                content = content.replace("```", "")
                
            print(f"OpenAI Response: {content}")
            return json.loads(content)
        except json.JSONDecodeError as e:
            error_msg = f"Error: Failed to parse JSON response - {str(e)}"
            print(f"OpenAI/JSON Error: {error_msg}")
            return error_msg
        except Exception as e:
            error_str = str(e)
            # Check if it's an authentication error
            if "401" in error_str or "auth" in error_str.lower():
                error_msg = f"Error: Authentication failed. Please check your API key in API Config. Details: {error_str}"
            else:
                error_msg = f"Error: {error_str}"
            print(f"OpenAI/JSON Error: {error_msg}")
            return error_msg