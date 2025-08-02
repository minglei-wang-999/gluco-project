import logging
from .gpt_client import GPTClient
import json
from typing import Union, Optional, Dict, Any
from .system_prompt import SYSTEM_PROMPT
import re

logger = logging.getLogger(__name__)

def extract_between_tags(text: str, start_tag: str, end_tag: str) -> list[str]:
    """
    Extract content between specified start and end tags.
    
    Args:
        text: Input text containing tagged content
        start_tag: Opening tag
        end_tag: Closing tag
        
    Returns:
        list[str]: List of strings found between the tags
    """
    pattern = f"{start_tag}(.*?){end_tag}"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches

async def analyze_food_image(
    image_url: str, gpt_client: GPTClient, context: Optional[Dict[str, Any]] = None
) -> dict:
    """
    Analyze food image using GPT-4 Vision.
    """
    try:
        # Convert context to user message if provided
        user_message = "\n\n"
        if context:
            if "previous_analysis" in context:
                user_message += "上次分析结果：\n"
                for ing in context["previous_analysis"]["ingredients"]:
                    user_message += f"{ing['name']}: {ing['portion']}克\n"
                user_message += "\n"
            if "user_comment" in context:
                user_message += f"用户评论：{context['user_comment']}\n"
            user_message += "请认真阅读用户反馈，输出修改后的营养分析。"
        else:
            user_message += "请根据用户上传的图片，生成准确的营养分析。"
        result = await gpt_client(
            image_url,
            SYSTEM_PROMPT,
            user_message
        )

        data = extract_between_tags(result, "<JSON>", "</JSON>")
        data = json.loads(data[0])
        notes = extract_between_tags(result, "<COMMENT>", "</COMMENT>")
        notes = notes[0]
        return {
            "ingredients": data["ingredients"],
            "notes": notes
        }
    except Exception as e:
        logger.error(result)
        logger.error(f"Error analyzing food image: {str(e)}")
        return None


