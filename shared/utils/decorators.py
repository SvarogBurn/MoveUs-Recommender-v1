from collections.abc import Callable
from functools import wraps
from typing import Any

import graphene

from core.redis_client import incr_sync
from shared.errors.mu_error import MUError, MUErrorCode


def require_auth(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(root: Any, info: graphene.ResolveInfo, *args: Any, **kwargs: Any) -> Any:
        user = info.context.user
        if not user.id:
            raise MUError(MUErrorCode.AUTHENTICATION_ERROR)
        return func(root, info, *args, **kwargs)

    return wrapper


def _client_ip(request: Any) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(scope: str, limit: int, period_seconds: int) -> Callable:
    """Per-IP fixed-window throttle for a graphene mutate method.

    Fails open if Redis is unavailable — better to serve traffic than to
    lock everyone out on a Redis blip. Auth abuse remains bounded by the
    upstream proxy / WAF in that case.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(root: Any, info: graphene.ResolveInfo, *args: Any, **kwargs: Any) -> Any:
            ip = _client_ip(info.context)
            key = f"ratelimit:{scope}:{ip}"
            count = incr_sync(key, ex=period_seconds)
            if count is not None and count > limit:
                raise MUError(MUErrorCode.RATE_LIMITED)
            return func(root, info, *args, **kwargs)

        return wrapper

    return decorator
