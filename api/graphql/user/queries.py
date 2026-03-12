import graphene

from main.user.models import User
from shared.errors.mu_error import MUError, MUErrorCode
from shared.utils.decorators import require_auth

from .types import ProfileType, UserType


class UserQuery(graphene.ObjectType):
    user = graphene.Field(UserType, id=graphene.Int(), username=graphene.String())

    def resolve_user(
        root,
        info: graphene.ResolveInfo,
        id: int | None = None,
        username: str | None = None,
        **kwargs,
    ) -> User:
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
    def resolve_my_profile(root, info: graphene.ResolveInfo, **kwargs) -> User:
        return info.context.user
