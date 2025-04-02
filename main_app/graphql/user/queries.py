import graphene
from graphql import GraphQLError

from .types import ProfileType, UserType
from ...models import MoveusUser, UserPrivacySetting
from ...models.enums import PrivacySetting, PrivacyScope

class UserQuery(graphene.ObjectType):
    users = graphene.List(UserType)
    user = graphene.Field(UserType, id = graphene.Int())

    def resolve_users(root, info, **kwargs):
        l =  MoveusUser.objects.all()
        return l
    
    def resolve_user(root, info, id, **kwargs):
        try:
            return MoveusUser.objects.get(pk=id)
        except MoveusUser.DoesNotExist:
            raise GraphQLError("User does not exist.")

class ProfileQuery(graphene.ObjectType):
    my_profile = graphene.Field(ProfileType)

    def resolve_my_profile(root, info, **kwargs):
        if info.context.user.id:
            return info.context.user;
        raise GraphQLError("Need to be authenticated")



