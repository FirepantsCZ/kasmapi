"""Models for the Kasm Workspaces API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self
from uuid import UUID  # noqa: TC003

import requests
from pydantic import BaseModel, PrivateAttr

from kasmapi.exceptions import UsageQuotaReachedError
from kasmapi.utils import REQUEST_TIMEOUT, Permissions, check_permissions

if TYPE_CHECKING:
    from kasmapi.kasm import Kasm


class KasmObject(BaseModel):
    """Base class for Kasm API objects."""

    _kasm: Kasm = PrivateAttr()

    @classmethod
    def from_api(cls, data: dict[str, Any], kasm: Kasm) -> Self:
        """Create an instance from an API response.

        Args:
            data: JSON data from the API response
            kasm: Kasm instance to associate with the object

        Returns:
            KasmObject or subclass instance
        """
        instance = cls.model_validate(data)
        instance._kasm = kasm
        return instance

    def __init_subclass__(cls, name: str | None = None, **kwargs: Any) -> None:  # noqa: ANN401
        """Called when a class is subclassed.

        This method is intended to allow customization of class creation
        by dynamically setting a name attribute for the subclass, if provided.

        Args:
            name (str | None): Optional name to assign as the subclass's name.
            **kwargs (Any): Arbitrary keyword arguments passed to the superclass.

        """
        super().__init_subclass__(**kwargs)
        if name:
            cls.__name__ = name


class Image(KasmObject):
    """Represents an image object."""

    image_id: UUID
    friendly_name: str


class Setting(KasmObject):
    """Represents a setting object."""

    group_id: UUID
    group_setting_id: UUID
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
                        "group_id": self.group_id.hex,
                    },
                    "target_setting": {
                        "group_setting_id": self.group_setting_id.hex,
                        "value": value,
                    },
                },
            ),
        )
        update_resp.raise_for_status()
        self.value = value


class Session(KasmObject, name="Kasm"):
    """Represents a session object."""

    kasm_id: UUID
    start_date: str
    image: Image
    operational_status: str
    user_id: UUID
    username: str
    expiration_date: str

    # A user: User = PrivateAttr() could be added here,
    # to be filled in by overriding from_api()
    # and calling self._kasm.get_user()
    #
    # Though publicly using an attribute
    # which is not part of the REST API spec is kinda yucky
    #
    # So for now, just leave it to the user to get the User from a Session
    # using Kasm.get_user()

    @check_permissions(
        [
            Permissions.USER,
            Permissions.USER_AUTH_SESSION,
        ]
    )
    def keepalive(self) -> None:
        update_resp = requests.post(
            f"{self._kasm.kasm_url}/api/public/keepalive",
            json=self._kasm._get_json({"kasm_id": self.kasm_id.hex}),
            timeout=REQUEST_TIMEOUT,
        )
        update_resp.raise_for_status()

        if update_resp.json()["usage_reached"]:
            raise UsageQuotaReachedError

    @check_permissions(
        [
            Permissions.USER,
            Permissions.USER_AUTH_SESSION,
        ]
    )
    def destroy(self) -> None:
        response = requests.post(
            f"{self._kasm.kasm_url}/api/public/destroy_kasm",
            json=self._kasm._get_json(
                {"kasm_id": self.kasm_id.hex, "user_id": self.user_id.hex}
            ),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        # TODO: Check for error in response


class Group(KasmObject):
    """Represents a group object."""

    group_id: UUID
    name: str
    _settings: list[Setting] = PrivateAttr()

    @classmethod
    def from_api(cls, data: dict[str, Any], kasm: Kasm) -> Group:
        """Create an instance from an API response.

        Overridden to assign `_settings` to the instance.
        """
        group = cls.model_validate(data)
        group._kasm = kasm
        group._settings = kasm.get_settings_group(group.group_id.hex)
        return group

    def get_setting(self, name: str) -> Setting | None:
        return next(filter(lambda setting: setting.name == name, self._settings), None)


class User(KasmObject):
    """Represents a user object."""

    user_id: UUID
    username: str
    groups: list[Group]

    @classmethod
    def from_api(cls, data: dict[str, Any], kasm: Kasm) -> User:
        """Create an instance from an API response.

        Overridden to assign `groups` to the instance.
        """
        user = cls.model_validate(data)
        user.groups = [Group.from_api(group, kasm) for group in data["groups"]]
        user._kasm = kasm
        return user

    @check_permissions(
        [
            Permissions.USER,
            Permissions.USER_AUTH_SESSION,
        ]
    )
    def request_session(
        self,
        image: Image,
        enable_sharing: bool = False,
        environment: dict[str, str] | None = None,
    ) -> Session:
        """Request the creation of a session with the given image.

        Args:
            image: The image to use for the session.
            enable_sharing: Whether to allow sharing of the session.
            environment: Environment variables to set in the session.

        Returns:
            The created Session object.
        """
        response = requests.post(
            f"{self._kasm.kasm_url}/api/public/request_kasm",
            json=self._kasm._get_json(
                {
                    "user_id": self.user_id.hex,
                    "image_id": image.image_id.hex,
                    "enable_sharing": enable_sharing,
                    "environment": environment,
                }
            ),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        # TODO: Return tuple of Session, SessionToken and maybe something else?
        return self.get_session(response.json()["kasm_id"])

    def get_session(self, session_id: str) -> Session:
        """Get a session by its ID.

        Args:
             session_id: The ID of the session to retrieve.

        Returns:
            The Session object.
        """
        response = requests.post(
            f"{self._kasm.kasm_url}/api/public/get_kasm_status",
            json=self._kasm._get_json(
                {
                    "kasm_id": session_id,
                    "user_id": self.user_id.hex,
                }
            ),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return Session.from_api(response.json()["kasm"], self._kasm)


class ApiConfig(KasmObject):
    """Represents an API configuration object."""

    api_id: UUID
    name: str
    api_key: str
    enabled: bool
    read_only: bool
    created: str
    last_used: str
    expires: str | None


class Permission(KasmObject):
    """Represents a permission object."""

    group_permission_id: UUID
    group_id: UUID | None
    permission_name: str
    permission_description: str
    permission_id: int | None
