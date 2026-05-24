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


def rate_limit(
    scope: str, limit: int, period_seconds: int, by: str = "ip"
) -> Callable:
    """Fixed-window throttle for a graphene mutate method.

    `by="ip"` keys on the request's client IP — right for unauthenticated
    endpoints (login, sign-up) where IP is the only stable handle.

    `by="user"` keys on the authenticated user id — right for authed actions
    where IP is too coarse (NAT/carriers) or too easy to rotate. Must be
    stacked *inside* @require_auth so `info.context.user.id` is set.

    Fails open if Redis is unavailable — better to serve traffic than to
    lock everyone out on a Redis blip.
    """

    if by not in ("ip", "user"):
        raise ValueError(f"rate_limit: unknown `by` mode {by!r}")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(root: Any, info: graphene.ResolveInfo, *args: Any, **kwargs: Any) -> Any:
            if by == "user":
                user_id = getattr(info.context.user, "id", None)
                if not user_id:
                    raise MUError(MUErrorCode.AUTHENTICATION_ERROR)
                handle = f"u:{user_id}"
            else:
                handle = f"ip:{_client_ip(info.context)}"

            key = f"ratelimit:{scope}:{handle}"
            count = incr_sync(key, ex=period_seconds)
            if count is not None and count > limit:
                raise MUError(MUErrorCode.RATE_LIMITED)
            return func(root, info, *args, **kwargs)

        return wrapper

    return decorator
