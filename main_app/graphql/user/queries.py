import graphene
from graphql import GraphQLError

from .types import ProfileType, UserType
from ...models import MoveusUser, UserPrivacySetting
from ...models.enums import PrivacySetting, PrivacyScope

class UserQuery(graphene.ObjectType):
    users = graphene.List(UserType)

    def resolve_users(root, info, **kwargs):
        l =  MoveusUser.objects.all()
        return l

class ProfileQuery(graphene.ObjectType):
    my_profile = graphene.Field(ProfileType)

    def resolve_my_profile(root, info, **kwargs):
        if info.context.user.id:
            return info.context.user;
        raise GraphQLError("Need to be authenticated")



