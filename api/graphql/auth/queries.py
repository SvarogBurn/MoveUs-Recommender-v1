import graphene

from main.user.models import User


class AuthUtilQuery(graphene.ObjectType):
    username_taken = graphene.Boolean(username=graphene.String(), required=True)

    email_taken = graphene.Boolean(email=graphene.String(), required=True)

    is_logged_in = graphene.Boolean()

    def resolve_username_taken(
        self, info: graphene.ResolveInfo, username: str
    ) -> bool:
        return User.objects.filter(username=username.lower()).exists()

    def resolve_email_taken(self, info: graphene.ResolveInfo, email: str) -> bool:
        return User.objects.filter(email=email).exists()

    def resolve_is_logged_in(self, info: graphene.ResolveInfo) -> bool:
        return bool(info.context.user)
