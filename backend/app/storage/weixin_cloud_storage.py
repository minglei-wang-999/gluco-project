import requests
from typing import Optional, Dict
import os
import time
from pathlib import Path


class WeixinCloudStorage:
    def __init__(
        self, app_id: str, app_secret: str, env_id: str, verify_ssl: bool = True
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.env_id = env_id
        self.base_url = "http://api.weixin.qq.com"
        self._access_token = None
        self._token_expires_at = 0
        self.verify_ssl = verify_ssl

    @property
    def access_token(self) -> str:
        """
        Get access token, refresh if expired

        Returns:
            str: Valid access token
        """
        now = time.time()
        if not self._access_token or now >= self._token_expires_at:
            self._refresh_token()
        return self._access_token

    def _refresh_token(self) -> None:
        """Refresh the access token"""
        url = f"{self.base_url}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }

        response = requests.get(url, params=params, verify=self.verify_ssl)
        result = response.json()

        if "access_token" not in result:
            raise Exception(f"Failed to get access token: {result}")

        self._access_token = result["access_token"]
        # Set expiration 5 minutes before actual expiry (default is 2 hours)
        self._token_expires_at = time.time() + result["expires_in"] - 300

    # def upload_file(self, file_path: str, cloud_path: Optional[str] = None) -> Dict:
    #     """
    #     Upload file to Weixin Cloud Storage

    #     Args:
    #         file_path: Local path to the file
    #         cloud_path: Path in cloud storage (e.g., "images/photo.jpg")

    #     Returns:
    #         dict: Response containing file_id and download_url
    #     """
    #     if not cloud_path:
    #         cloud_path = os.path.basename(file_path)

    #     cloud_path = cloud_path.replace("\\", "/").lstrip("/")

    #     # Step 1: Get upload URL and token
    #     upload_url = f"{self.base_url}/tcb/uploadfile"
    #     query_params = {
    #         "access_token": self.access_token
    #     }

    #     json_data = {
    #         "env": self.env_id,
    #         "path": cloud_path
    #     }

    #     response = requests.post(
    #         upload_url,
    #         params=query_params,
    #         json=json_data,
    #         headers={"Content-Type": "application/json"}
    #     )

    #     upload_info = response.json()
    #     # print("Debug - Step 1 response:", upload_info)  # Debug info

    #     if "errcode" in upload_info and upload_info["errcode"] != 0:
    #         raise Exception(f"Failed to get upload URL: {upload_info}")

    #     # Step 2: Upload the file to COS
    #     with open(file_path, "rb") as f:
    #         files = {
    #             "file": (cloud_path, f, "application/octet-stream")
    #         }

    #         form_data = {
    #             "key": cloud_path,
    #             "Signature": upload_info["authorization"],
    #             "x-cos-security-token": upload_info["token"],
    #             "x-cos-meta-fileid": upload_info["cos_file_id"]
    #         }

    #         # print("Debug - Upload URL:", upload_info["url"])  # Debug info
    #         # print("Debug - Form data:", form_data)  # Debug info

    #         response = requests.post(
    #             upload_info["url"],
    #             data=form_data,
    #             files=files
    #         )

    #         print("Debug - Step 2 response:", response.text)  # Debug info
    #         print("Debug - Step 2 status:", response.status_code)  # Debug info

    #         if response.status_code in [200, 204]:
    #             return {
    #                 "file_id": upload_info.get("file_id"),
    #                 "url": upload_info.get("url", ""),
    #                 "token": upload_info.get("token", ""),
    #                 "cloud_path": cloud_path,
    #                 "raw_response": upload_info
    #             }
    #         raise Exception(f"Upload failed (status {response.status_code}): {response.text}")

    def get_download_url(self, file_id: str) -> str:
        """
        Get download URL for a file

        Args:
            file_id: File ID from upload response

        Returns:
            str: Download URL
        """
        url = f"{self.base_url}/tcb/batchdownloadfile"
        # query_params = {"access_token": self.access_token}
        json_data = {
            "env": self.env_id,
            "file_list": [
                {"fileid": file_id, "max_age": 7200}  # URL valid for 2 hours
            ],
        }

        # print("Debug - Download request URL:", url)  # Debug info
        # print("Debug - Download request params:", query_params)  # Debug info
        # print("Debug - Download request data:", json_data)  # Debug info

        response = requests.post(
            url, json=json_data, verify=self.verify_ssl
        )
        result = response.json()

        # print("Debug - Download response:", result)  # Debug info

        if result.get("errcode", 0) != 0:
            raise Exception(
                f"Failed to get download URL: {result.get('errmsg', 'Unknown error')}"
            )

        if not result.get("file_list") or not result["file_list"][0].get(
            "download_url"
        ):
            raise Exception("No download URL in response")

        return result["file_list"][0]["download_url"]
