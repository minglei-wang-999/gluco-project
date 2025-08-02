"""
Module for handling GPT API interactions.
"""
import os
import json
import logging
from openai import OpenAI
from typing import List, Dict, Any
from functools import lru_cache
import re

logger = logging.getLogger(__name__)


def repair_json_str(text: str) -> str:
    """Repair JSON string that may contain syntax issues.
    Only fixes JSON syntax problems, not semantic validation.
    """
    # Remove // style comments
    repaired_text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    
    # Replace Chinese punctuation with ASCII equivalents
    repaired_text = repaired_text.replace('，', ',')
    repaired_text = repaired_text.replace('：', ':')
    
    # Fix incomplete values
    # json_str = re.sub(r':\s*-\s*([,}])', ': 0\\1', json_str)  # Fix lone "-" value
    # json_str = re.sub(r':\s*([,}])', ': 0\\1', json_str)      # Fix missing value
    # json_str = re.sub(r':\s*"_"\s*([,}])', ': 0\\1', json_str)  # Fix underscore value
    # json_str = re.sub(r':\s*"_"\s*', ': 0', json_str)  # Convert underscore string to 0
    
    # Clean up whitespace
    # json_str = re.sub(r'\s*,\s*', ', ', json_str)
    # json_str = re.sub(r'\s*:\s*', ': ', json_str)
    # json_str = re.sub(r'\s+$', '', json_str, flags=re.MULTILINE)
    
    # Remove trailing commas
    repaired_text = re.sub(r',\s*([}\]])', r'\1', repaired_text)
    repaired_text = re.sub(r',\s*$', '', repaired_text)
    
    # Add missing closing brackets/braces if needed
    # open_brackets = json_str.count('[')
    # close_brackets = json_str.count(']')
    # open_braces = json_str.count('{')
    # close_braces = json_str.count('}')
    
    # json_str = json_str.rstrip(',\t \n')
    # if open_brackets > close_brackets:
    #     json_str += '}' * (open_braces - close_braces) + ']' * (open_brackets - close_brackets)
    # elif open_braces > close_braces:
    #     json_str += '}' * (open_braces - close_braces)
    
    # try:
    #     # Try to parse and re-serialize to ensure valid JSON
    #     data = json.loads(json_str)
    #     return json.dumps(data)
    # except json.JSONDecodeError:
    #     return json_str
    return repaired_text

class GPTClient:
    def __init__(self):
        self.text_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.vision_client = OpenAI(
            api_key=os.getenv("OPENAI_VISION_API_KEY"),
            base_url=os.getenv("OPENAI_VISION_BASE_URL"),
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.vision_model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
        self.vision_max_tokens = int(os.getenv("OPENAI_VISION_MAX_TOKENS", "1000"))

    @lru_cache(maxsize=100)
    async def __call__(
        self,
        image_url: str,
        system_message: str,
        user_message: str,
        response_format: str = None,
    ) -> dict | str:
        """
        Analyze an image using GPT-4 Vision.

        Args:
            image_url: URL of the image
            system_message: The system message defining GPT's role and response format

        Returns:
            dict: Parsed JSON response, or None if request fails
        """
        try:
            # Check if the input is a URL or base64 data
            if image_url.startswith(("http://", "https://")):
                image_content = {"url": image_url}
            else:
                # Ensure the base64 data has the correct prefix
                image_data = image_url
                if not image_data.startswith("data:image/"):
                    image_data = f"data:image/jpeg;base64,{image_data}"
                image_content = {"url": image_data}

            response = self.vision_client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {
                        "role": "user",
                        "content": [{"type": "image_url", "image_url": image_content}],
                    },
                    {"role": "user", "content": user_message},
                ],
                max_tokens=self.max_tokens,
                response_format={"type": "text"}
                if response_format is None
                else {"type": response_format},
            )

            logger.info("Successfully analyzed image with GPT Vision")

            if response_format == "json_object":
                # qwen2.5 VL model not good at json response
                data = response.choices[0].message.content
                if data.startswith("```json"):
                    data = data[len("```json") :]
                data = data.split("```")[0]

                repaired_data = repair_json_str(data)
                try:
                    result = json.loads(repaired_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON: {str(e)}")
                    logger.error(f"Original data: {data}")
                    logger.error(f"Repaired data: {repaired_data}")
                    result = None
                return result
            else:
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error analyzing image with GPT Vision: {str(e)}")
            return None

    async def get_json_response(
        self, system_message: str, user_message: str
    ) -> dict:
        """
        Get a JSON response from GPT using text-only query.

        Args:
            system_message: The system message defining GPT's role and response format
            user_message: The user message to send to GPT

        Returns:
            dict: Parsed JSON response, or None if request fails
        """
        try:
            response = self.text_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )

            logger.info("Successfully got JSON response from GPT")
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error getting JSON response from GPT: {str(e)}")
            return None
