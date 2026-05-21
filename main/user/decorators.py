from functools import wraps

from shared.enums import PrivacySetting


def _viewer_id(info) -> int | None:
    """The authenticated viewer's id, or None for anonymous requests."""
    viewer = getattr(info.context, "user", None)
    if viewer is None or getattr(viewer, "is_anonymous", True):
        return None
    return viewer.id


def privacy_gated(setting: PrivacySetting):
    def decorator(func):
        @wraps(func)
        def wrapper(self, info, *args, **kwargs):
            from main.user.services import UserService

            viewer_id = _viewer_id(info)
            if self.id != viewer_id:
                cache = getattr(info.context, "_privacy_cache", None)
                if cache is None:
                    cache = {}
                    setattr(info.context, "_privacy_cache", cache)

                bool_key = (self.id, setting)
                if bool_key not in cache:
                    map_key = ("map", self.id)
                    if map_key not in cache:
                        cache[map_key] = UserService.get_privacy_map(self.id)
                    cache[bool_key] = UserService.check_privacy(
                        self.id, viewer_id, setting, scope_map=cache[map_key]
                    )

                if not cache[bool_key]:
                    return None
            return func(self, info, *args, **kwargs)

        return wrapper

    return decorator
