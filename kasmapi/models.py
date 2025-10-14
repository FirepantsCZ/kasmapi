from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

import requests
from pydantic import BaseModel, PrivateAttr

from kasmapi.exceptions import UsageQuotaReachedError
from kasmapi.utils import Permissions, check_permissions

if TYPE_CHECKING:
    from kasmapi.kasm import Kasm

# TODO: Add a @check_permissions decorator
#   to generate pretty errors if needed permissions are not met.
#   relevant endpoints are: /get_permissions and /get_permissions_group

class KasmObject(BaseModel):
    _kasm: Kasm = PrivateAttr()

    @classmethod
    def from_api(cls, data: dict[str, Any], kasm: Kasm) -> Self:
        instance = cls.model_validate(data)
        instance._kasm = kasm
        return instance


class Image(KasmObject):
    friendly_name: str


class Setting(KasmObject):
    group_id: str
    group_setting_id: str
    description: str
    name: str
    value: str | int

    # TODO: Move _get_json to KasmObject and maybe rename it and change to public?
    #   Either way, find a better way to do this
    def set_value(self, value: str | int) -> None:
        # print(f"setting value of '{self.name}' to {value}")
        update_resp = requests.post(
            f"{self._kasm.kasm_url}/api/admin/update_settings_group",
            json=self._kasm._get_json(
                {
                    "target_group": {
                        "group_id": self.group_id,
                    },
                    "target_setting": {
                        "group_setting_id": self.group_setting_id,
                        "value": value,
                    },
                },
            ),
        )
        update_resp.raise_for_status()
        self.value = value


class Session(KasmObject):
    kasm_id: str
    start_date: str
    image: Image
    operational_status: str
    user_id: str
    username: str
    expiration_date: str

    @check_permissions([
        Permissions.USER,
        Permissions.USER_AUTH_SESSION,
    ])
    def keepalive(self) -> None:
        update_resp = requests.post(
            f"{self._kasm.kasm_url}/api/public/keepalive",
            json=self._kasm._get_json({"kasm_id": self.kasm_id}),
        )
        update_resp.raise_for_status()

        if update_resp.json()["usage_reached"]:
            raise UsageQuotaReachedError

    @check_permissions([
        Permissions.USER,
        Permissions.USER_AUTH_SESSION,
    ])
    def destroy(self) -> None:
        response = requests.post(
            f"{self._kasm.kasm_url}/api/public/destroy_kasm",
            json=self._kasm._get_json({"kasm_id": self.kasm_id, "user_id": self.user_id}),
        )
        response.raise_for_status()
        # TODO: Check for error in response


class Group(KasmObject):
    group_id: str
    name: str
    _settings: list[Setting] = PrivateAttr()

    @classmethod
    def from_api(cls, data: dict[str, Any], kasm: Kasm) -> Group:
        group = cls.model_validate(data)
        group._kasm = kasm
        group._settings = kasm.get_settings_group(group.group_id)
        return group

    def get_setting(self, name: str) -> Setting | None:
        return next(filter(lambda setting: setting.name == name, self._settings), None)


class User(KasmObject):
    user_id: str
    username: str
    groups: list[Group]

    @classmethod
    def from_api(cls, data: dict[str, Any], kasm: Kasm) -> User:
        user = cls.model_validate(data)
        user.groups = [Group.from_api(group, kasm) for group in data["groups"]]
        user._kasm = kasm
        return user

class ApiConfig(KasmObject):
    api_id: str
    name: str
    api_key: str
    enabled: bool
    read_only: bool
    created: str
    last_used: str
    expires: str | None


class Permission(KasmObject):
    group_permission_id: str
    group_id: str | None
    permission_name: str
    permission_description: str
    permission_id: int | None