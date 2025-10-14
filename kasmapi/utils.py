from enum import Enum
from typing import Iterable, Callable, Any, TYPE_CHECKING
from functools import wraps
from kasmapi.exceptions import ApiPermissionError

if TYPE_CHECKING:
    from kasmapi.models import ApiConfig
    from kasmapi.kasm import Kasm

class Permissions(Enum):
    USER = "User"
    USER_AUTH_SESSION = "Users Auth Session"

def check_permissions(required_permissions: Iterable[Permissions]) -> Any:
    def decorator(function: Any) -> Callable[..., Any]:
        @wraps(function)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            _kasm: Kasm | None = getattr(self, "_kasm", None)
            if _kasm is None:
                raise RuntimeError("ERROR: No _kasm instance found in object, something is seriously wrong.")

            api_config: ApiConfig = next(filter(lambda config: config.api_key == _kasm.api_key, _kasm.get_api_configs()))
            current_permissions = [permission.permission_name for permission in _kasm.get_permissions_group(api_config)]

            if missing_permissions := list(filter(lambda permission: permission.value not in current_permissions, required_permissions)):
                msg = f"Missing permissions for '{api_config.name}': {missing_permissions}"
                raise ApiPermissionError(msg)

            result = function(self, *args, **kwargs)
            return result

        return wrapper

    return decorator
