from enum import Enum
from typing import Iterable, Callable, Any, TYPE_CHECKING
from functools import wraps
from kasmapi.exceptions import ApiPermissionError

if TYPE_CHECKING:
    from kasmapi.models import ApiConfig

class Permissions(Enum):
    USER = "User"
    USER_AUTH_SESSION = "Users Auth Session"
    IMAGES_VIEW = "Images View"
    USERS_VIEW = "Users View"

from typing import Any, Callable, Iterable, TypeVar, ParamSpec
from functools import wraps

P = ParamSpec("P")
R = TypeVar("R")

def check_permissions(required_permissions: Iterable[Permissions]) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            from kasmapi.kasm import Kasm

            if not args:
                raise RuntimeError("ERROR: Decorated method called without arguments, cannot find 'self'.")
            self = args[0]  # assumes the first arg is `self`

            _kasm: Kasm | None = getattr(self, "_kasm", None) or (self if isinstance(self, Kasm) else None)
            if _kasm is None:
                raise RuntimeError("ERROR: No _kasm instance found in object, something is seriously wrong.")

            api_config: ApiConfig = next(
                filter(lambda config: config.api_key == _kasm.api_key, _kasm.get_api_configs())
            )
            current_permissions = [permission.permission_name for permission in _kasm.get_permissions_group(api_config)]

            if missing_permissions := [
                permission for permission in required_permissions if permission.value not in current_permissions
            ]:
                msg = f"Missing permissions for '{api_config.name}': {missing_permissions}"
                raise ApiPermissionError(msg)

            return function(*args, **kwargs)

        return wrapper

    return decorator
