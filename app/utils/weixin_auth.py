"""WeChat authentication utilities."""
import os
import aiohttp
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)


async def get_weixin_openid(code: str) -> Optional[str]:
    """Get WeChat openid using the code from WeChat mini program."""
    appid = os.getenv("WEIXIN_APPID")
    secret = os.getenv("WEIXIN_SECRET")

    logger.info("Getting WeChat openid for code: %s", code)
    logger.info("Using APPID: %s", appid)
    logger.info("Secret length: %d chars", len(secret) if secret else 0)

    if not appid or not secret:
        logger.debug(
            "WeChat credentials missing - APPID: %s, SECRET: %s",
            "present" if appid else "missing",
            "present" if secret else "missing",
        )
        return None

    url = "http://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": appid,
        "secret": secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }

    try:
        async with aiohttp.ClientSession() as session:
            logger.info("Making request to WeChat API: %s", url)
            logger.info(
                "With params (excluding secret): {'appid': %s, 'js_code': %s, 'grant_type': %s}",
                params["appid"],
                params["js_code"],
                params["grant_type"],
            )
            async with session.get(url, params=params) as response:
                logger.info("WeChat API response status: %d", response.status)
                if response.status == 200:
                    try:
                        # First try to get JSON directly
                        data = await response.json()
                    except aiohttp.ContentTypeError:
                        # If that fails, get text and parse it as JSON
                        text = await response.text()
                        logger.info("Got text response: %s", text)
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError as e:
                            logger.error("Failed to parse response as JSON: %s", e)
                            return None

                    logger.info("WeChat API response data: %s", data)
                    if "openid" in data:
                        logger.info("Successfully got openid")
                        return data["openid"]
                    elif "errcode" in data:
                        logger.error("WeChat API error: %s", data)
                        if data.get("errcode") == 40029:
                            logger.error("Invalid code provided")
                        elif data.get("errcode") == 40013:
                            logger.error("Invalid appid")
                        elif data.get("errcode") == 40125:
                            logger.error("Invalid secret")
                        return None
                else:
                    logger.error(
                        "WeChat API request failed with status %d", response.status
                    )
                    response_text = await response.text()
                    logger.error("Response body: %s", response_text)
                    return None

    except Exception as e:
        logger.error("Error getting WeChat openid: %s", str(e))
        logger.exception(e)  # This will log the full traceback
        return None
