import graphene

from main_app.util import require_auth

from ...models import User
from ..error import MUError, MUErrorCode
from .types import ProfileType, UserType


class UserQuery(graphene.ObjectType):
    user = graphene.Field(
        UserType, 
        id=graphene.Int(),
        username=graphene.String()
    )

    def resolve_user(root, info, id=None, username=None, **kwargs):
        if not id and not username:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)
        
        if id and username:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)
        
        try:
            if id:
                return User.objects.get(pk=id)
            else:
                return User.objects.get(username=username)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

class ProfileQuery(graphene.ObjectType):
    my_profile = graphene.Field(ProfileType)

    @require_auth
    def resolve_my_profile(root, info, **kwargs):
        return info.context.user



