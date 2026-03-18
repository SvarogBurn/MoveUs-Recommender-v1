import graphene

from main.auth.services import AuthService


class AuthUtilQuery(graphene.ObjectType):
    username_taken = graphene.Boolean(username=graphene.String(), required=True)
    email_taken = graphene.Boolean(email=graphene.String(), required=True)
    is_logged_in = graphene.Boolean()

    def resolve_username_taken(
        self, info: graphene.ResolveInfo, username: str
    ) -> bool:
        return AuthService.is_username_taken(username)

    def resolve_email_taken(self, info: graphene.ResolveInfo, email: str) -> bool:
        return AuthService.is_email_taken(email)

    def resolve_is_logged_in(self, info: graphene.ResolveInfo) -> bool:
        return AuthService.is_logged_in(info.context)
