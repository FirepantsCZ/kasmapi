"""Client for interacting with the Kasm Workspaces HTTP API.

Exposes the Kasm class, a lightweight wrapper around selected public and
admin endpoints that returns strongly typed model objects.
"""

# TODO: REPLACE ALL USAGES OF requests.post/get() WITH _get_model(s)()
# TODO: Add unit tests

import json
from collections.abc import Mapping
from typing import Any

import requests

from kasmapi.models import (
    ApiConfig,
    Image,
    KasmObject,
    Permission,
    Session,
    Setting,
    User,
)
from kasmapi.utils import REQUEST_TIMEOUT, Permissions, check_permissions


class Kasm:
    """High-level API client for Kasm Workspaces.

    This client authenticates using an API key and secret and provides
    convenience methods that wrap HTTP endpoints and materialize responses
    into model objects such as User, Image, and Session.
    """

    def __init__(self, kasm_url: str, api_key: str, api_key_secret: str) -> None:
        """Initialize the client.

        Args:
            kasm_url: Base URL of the Kasm deployment (e.g., "https://example.com").
            api_key: API key used for authentication.
            api_key_secret: API key secret used for authentication.
        """
        self.kasm_url = kasm_url
        self.api_key = api_key
        self.api_key_secret = api_key_secret

    def _api_post(
        self,
        path: str,
        body: dict[str, Any] | None,
        headers: Mapping[str, str | bytes | None] | None = None,
    ) -> dict[str, Any]:
        """Sends a POST request to the specified API endpoint.

        Including the provided JSON
        payload, and processes the response.

        Args:
            path: The API endpoint path as a string.
            body: The JSON payload to be included in the request body as a dictionary
                containing string keys and values that can be strings or integers.
            headers: Headers of the request.

        Returns:
            The parsed JSON response from the API as a Python object, whose type
            may vary depending on the API response.
        """
        response = requests.post(
            f"{self.kasm_url}/api/{path}",
            json=self._get_json(body),
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    def _api_get(
        self, path: str, headers: Mapping[str, str | bytes | None] | None = None
    ) -> dict[str, Any]:
        """Sends a GET request to the specified API endpoint.

        Args:
            path: The API endpoint path as a string.
            headers: Headers to include

        Returns:
            The parsed JSON response from the API as a Python object, whose type
            may vary depending on the API response.
        """
        response = requests.get(
            f"{self.kasm_url}/api/{path}",
            timeout=REQUEST_TIMEOUT,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    def _get_models[M: KasmObject](
        self,
        model_type: type[M],
        path: str,
        body: dict[str, Any] | None = None,
        post: bool = True,
        headers: Mapping[str, str | bytes | None] | None = None,
    ) -> list[M]:
        if post:
            response = self._api_post(path, body, headers)
        else:
            response = self._api_get(path, headers)

        # When I eventually get sick of playing with this,
        # an actually useful and not ridiculous use-case
        # would be having an attribute on KasmObjects that denote
        # their API response name (or names for iterables) for use in this function
        return [
            model_type.from_api(model, self)
            for model in response[f"{model_type.__name__.lower()}s"]
        ]

    def _get_model[M: KasmObject](
        self,
        model_type: type[M],
        path: str,
        body: dict[str, Any] | None = None,
        post: bool = True,
        headers: Mapping[str, str | bytes | None] | None = None,
    ) -> M:
        if post:
            response = self._api_post(path, body, headers)
        else:
            response = self._api_get(path, headers)

        return model_type.from_api(response[model_type.__name__.lower()], self)

    def get_user(self, user_id: str, user_name: str) -> User:
        """Fetch a single user by ID and username.

        Args:
            user_id: Unique identifier of the user.
            user_name: Username of the user.

        Returns:
            A populated User instance.

        Raises:
            requests.HTTPError: If the HTTP request fails with a non-2xx status.
        """
        return self._get_model(
            User,
            "public/get_user",
            {
                "target_user": {
                    "user_id": user_id,
                    "username": user_name,
                }
            },
        )

    @check_permissions(
        [
            Permissions.USERS_VIEW,
        ]
    )
    def get_users(self) -> list[User]:
        """List users visible to the caller.

        Requires:
            Permissions.USERS_VIEW.

        Returns:
            A list of User instances.

        Raises:
            requests.HTTPError: If the HTTP request fails with a non-2xx status.
        """
        return self._get_models(
            User,
            "public/get_users",
        )

    def _get_json(self, request_json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Compose the JSON payload for API requests.

        Merges the provided request_json with authentication fields.

        Args:
            request_json: Optional request-specific payload to include.

        Returns:
            The final payload dictionary including authentication fields and any
            additional request data.
        """
        result = {
            "api_key": self.api_key,
            "api_key_secret": self.api_key_secret,
        }
        if request_json:
            result.update(request_json)
        return result

    def get_settings_group(self, group_id: str) -> list[Setting]:
        """Fetch all settings in the specified settings group.

        Args:
            group_id: Identifier of the settings group.

        Returns:
            A list of Setting instances belonging to the group.

        Raises:
            requests.HTTPError: If the HTTP request fails with a non-2xx status.
        """
        response = requests.post(
            f"{self.kasm_url}/api/admin/get_settings_group",
            json=self._get_json({"target_group": {"group_id": group_id}}),
        )
        response.raise_for_status()
        return [
            Setting.from_api(setting, self) for setting in response.json()["settings"]
        ]

    @check_permissions(
        [
            Permissions.IMAGES_VIEW,
        ]
    )
    def get_images(self) -> list[Image]:
        """List images visible to the caller.

        Requires:
            Permissions.IMAGES_VIEW.

        Returns:
            A list of Image instances.

        Raises:
            requests.HTTPError: If the HTTP request fails with a non-2xx status.
        """
        response = requests.post(
            f"{self.kasm_url}/api/public/get_images",
            json=self._get_json(),
        )
        response.raise_for_status()
        return [Image.from_api(image, self) for image in response.json()["images"]]

    def get_api_configs(self) -> list[ApiConfig]:
        """Retrieve available API configuration objects.

        Returns:
            A list of ApiConfig instances.

        Raises:
            requests.HTTPError: If the HTTP request fails with a non-2xx status.
        """
        response = requests.post(
            f"{self.kasm_url}/api/admin/get_api_configs",
            json=self._get_json(),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return [
            ApiConfig.from_api(api_config, self)
            for api_config in response.json()["api_configs"]
        ]

    def get_permissions_group(self, target_api_config: ApiConfig) -> list[Permission]:
        """Retrieve permissions associated with a given API configuration.

        Args:
            target_api_config: The ApiConfig instance to query permissions for.

        Returns:
            A list of Permission instances.

        Raises:
            requests.HTTPError: If the HTTP request fails with a non-2xx status.
        """
        response = requests.post(
            f"{self.kasm_url}/api/admin/get_permissions_group",
            json=self._get_json(
                {"target_api_config": json.loads(target_api_config.model_dump_json())}
            ),
        )
        response.raise_for_status()
        return [
            Permission.from_api(api_config, self)
            for api_config in response.json()["permissions"]
        ]

    def get_sessions(self) -> list[Session]:
        """List active sessions visible to the caller.

        Returns:
            A list of Session instances.

        Raises:
            requests.HTTPError: If the HTTP request fails with a non-2xx status.
        """
        return self._get_models(
            Session,
            "public/get_kasms",
        )
