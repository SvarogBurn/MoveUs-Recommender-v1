import graphene

from .types import UserType
from ...models import MoveusUser, UserPrivacySetting
from ...models.enums import PrivacySetting, PrivacyScope

class UserQuery(graphene.ObjectType):
    users = graphene.List(UserType)

    def resolve_users(root, info, **kwargs):
        l =  MoveusUser.objects.all()
        return l

class ProfileQuery(graphene.ObjectType):
    profile = graphene.Field(UserType)

    def resolve_profile(root, info, **kwargs):
        if info.context.user.id:
            return info.context.user;
        return "Need to be authenticated"



