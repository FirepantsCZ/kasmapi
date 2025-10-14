from typing import Any, Iterable

import requests

from kasmapi.models import Session, Setting, User, ApiConfig, Permission

class Kasm:
    def __init__(self, kasm_url: str, api_key: str, api_key_secret: str):
        self.kasm_url = kasm_url
        self.api_key = api_key
        self.api_key_secret = api_key_secret

    def get_user(self, user_id: str, user_name: str) -> User:
        response = requests.post(
            f"{self.kasm_url}/api/public/get_user",
            json=self._get_json(
                {
                    "target_user": {
                        "user_id": user_id,
                        "username": user_name,
                    },
                },
            ),
        )
        response.raise_for_status()
        return User.from_api(response.json()["user"], self)

    def _get_json(self, request_json: dict[str, Any] | None = None) -> dict[str, Any]:
        result = {
            "api_key": self.api_key,
            "api_key_secret": self.api_key_secret,
        }
        if request_json:
            result.update(request_json)
        return result

    def get_settings_group(self, group_id: str) -> list[Setting]:
        response = requests.post(
            f"{self.kasm_url}/api/admin/get_settings_group",
            json=self._get_json({"target_group": {"group_id": group_id}}),
        )
        response.raise_for_status()
        return [
            Setting.from_api(setting, self) for setting in response.json()["settings"]
        ]

    def get_api_configs(self) -> list[ApiConfig]:
        response = requests.post(
            f"{self.kasm_url}/api/admin/get_api_configs",
            json=self._get_json(),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return [ApiConfig.from_api(api_config, self) for api_config in response.json()["api_configs"]]

    def get_permissions_group(self, target_api_config: ApiConfig) -> list[Permission]:
        response = requests.post(
            f"{self.kasm_url}/api/admin/get_permissions_group",
            json=self._get_json({"target_api_config": target_api_config.model_dump()}),
        )
        response.raise_for_status()
        return [Permission.from_api(api_config, self) for api_config in response.json()['permissions']]

    def get_sessions(self) -> list[Session]:
        sessions_resp = requests.post(
            f"{self.kasm_url}/api/public/get_kasms",
            json=self._get_json(),
        )
        sessions_resp.raise_for_status()
        return [
            Session.from_api(session, self) for session in sessions_resp.json()["kasms"]
        ]

