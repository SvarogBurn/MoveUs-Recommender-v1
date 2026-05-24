import graphene

from main.auth.services import AuthService


class AuthUtilQuery(graphene.ObjectType):
    is_logged_in = graphene.Boolean()

    def resolve_is_logged_in(self, info: graphene.ResolveInfo) -> bool:
        return AuthService.is_logged_in(info.context)
