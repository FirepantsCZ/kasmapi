import requests

from kasmapi.models import Session, User, Setting


class Kasm:
    def __init__(self, kasm_url: str, api_key: str, api_key_secret: str):
        self.kasm_url = kasm_url
        self.api_key = api_key
        self.api_key_secret = api_key_secret

    def get_user(self, user_id, user_name) -> User:
        response = requests.post(
            f"{self.kasm_url}/api/public/get_user",
            json=self._get_json({
                "target_user": {
                    "user_id": user_id,
                    "username": user_name,
                }
            }),
            verify=True
        )
        response.raise_for_status()
        return User.from_api(response.json()['user'], self)

    def _get_json(self, request_json = None):
        result = {
            "api_key": self.api_key,
            "api_key_secret": self.api_key_secret,
        }
        if request_json:
            result.update(request_json)
        return result

    def get_settings_group(self, group_id) -> list[Setting]:
        response = requests.post(
            f"{self.kasm_url}/api/admin/get_settings_group",
            verify=True,
            json=self._get_json({"target_group": {"group_id": group_id}}),
        )
        response.raise_for_status()
        return [Setting.from_api(setting, self) for setting in response.json()['settings']]

    def get_keepalive(self, group_id):
        keepalive_resp = requests.post(
            f"{self.kasm_url}/api/admin/get_settings_group",
            verify=True,
            json=self._get_json({"target_group": {"group_id": group_id}}),
        )
        keepalive_resp.raise_for_status()
        keepalive = next(
            filter(lambda setting: setting['name'] == "keepalive_expiration", keepalive_resp.json()['settings']))[
            'value']
        return keepalive

    def get_sessions(self) -> list[Session]:
        sessions_resp = requests.post(
            f"{self.kasm_url}/api/public/get_kasms",
            verify=True,
            json=self._get_json(),
        )
        sessions_resp.raise_for_status()
        return [Session.from_api(session, self) for session in sessions_resp.json()["kasms"]]

