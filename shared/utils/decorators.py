from collections.abc import Callable
from functools import wraps
from typing import Any

import graphene

from shared.errors.mu_error import MUError, MUErrorCode


def require_auth(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(root: Any, info: graphene.ResolveInfo, *args: Any, **kwargs: Any) -> Any:
        user = info.context.user
        if not user.id:
            raise MUError(MUErrorCode.AUTHENTICATION_ERROR)
        return func(root, info, *args, **kwargs)

    return wrapper
