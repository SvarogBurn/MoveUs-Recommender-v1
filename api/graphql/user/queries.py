import graphene

from main.user.models import User
from main.user.services import UserService
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
        return UserService.get_user(id=id, username=username)


class ProfileQuery(graphene.ObjectType):
    my_profile = graphene.Field(ProfileType)

    @require_auth
    def resolve_my_profile(root, info: graphene.ResolveInfo, **kwargs) -> User:
        return info.context.user
