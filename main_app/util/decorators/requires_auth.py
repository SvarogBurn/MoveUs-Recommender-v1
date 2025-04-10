from functools import wraps

from main_app.graphql.error import MUError, MUErrorCode
from main_app.models.user import User

def require_auth(func):
    @wraps(func)
    def wrapper(root, info, *args, **kwargs):
        user: User = info.context.user
        if not user.id:
            raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)
        return func(root, info, *args, **kwargs)
    return wrapper