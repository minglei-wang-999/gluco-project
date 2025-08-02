import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import base64
from pprint import pprint

# Add only the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.gpt_client import GPTClient
from prompt import SYSTEM_PROMPT

load_dotenv(".env.qwen")


def encode_image(image_path: str) -> str:
    """
    Load an image file and encode it as base64.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        str: Base64 encoded image with data URI scheme
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded_string}"


async def main():
    gpt_client = GPTClient()

    # gpt_client.vision_model = "qwen2.5-vl-32b-instruct"
    gpt_client.vision_model = "qwen2.5-vl-72b-instruct"
    # gpt_client.vision_model = "qwen-vl-plus-2025-01-25"
    # gpt_client.vision_model = "qwen2.5-vl-7b-instruct"
    
    # Replace this with your local image path
    image_path = "tests/assets/WechatIMG1173.jpg"
    
    # Optional context for testing
    
    try:
        # Encode the local image
        encoded_image = encode_image(image_path)
        

        result = await gpt_client(
            image_url=encoded_image,
            system_message=SYSTEM_PROMPT,
            user_message=""
        )
        
        print("\nAnalysis Result:")
        print(result)
        
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
    except Exception as e:
        print(f"Error during analysis: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
