import graphene

from api.graphql.user.types import ProfileType
from main.auth.services import AuthService
from shared.utils.decorators import rate_limit, require_auth


class LoginMutation(graphene.Mutation):

    class Arguments:
        user = graphene.String(required=True)
        password = graphene.String(required=True)
        remember_me = graphene.Boolean(default_value=False)

    my_profile = graphene.Field(ProfileType)

    @rate_limit("login", limit=10, period_seconds=60)
    def mutate(
        self,
        info: graphene.ResolveInfo,
        user: str,
        password: str,
        remember_me: bool = False,
    ):
        profile = AuthService.login(
            info.context, user, password, remember_me=remember_me
        )
        return LoginMutation(my_profile=profile)


class SignUpMutation(graphene.Mutation):

    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        remember_me = graphene.Boolean(default_value=False)

    my_profile = graphene.Field(ProfileType)

    @rate_limit("sign_up", limit=5, period_seconds=3600)
    def mutate(
        self,
        info: graphene.ResolveInfo,
        username: str,
        email: str,
        password: str,
        remember_me: bool = False,
    ):
        profile = AuthService.sign_up(
            info.context, email, username, password, remember_me=remember_me
        )
        return SignUpMutation(my_profile=profile)


class LogoutMutation(graphene.Mutation):
    success = graphene.Boolean()

    def mutate(self, info: graphene.ResolveInfo) -> "LogoutMutation":
        AuthService.logout(info.context)
        return LogoutMutation(success=True)


class DeleteAccountMutation(graphene.Mutation):
    success = graphene.Boolean()

    def mutate(self, info: graphene.ResolveInfo) -> "DeleteAccountMutation":
        AuthService.delete_account(info.context)
        return DeleteAccountMutation(success=True)


class SendConfirmationEmailMutation(graphene.Mutation):
    success = graphene.Boolean()

    @require_auth
    @rate_limit("send_confirmation_email", limit=3, period_seconds=3600)
    def mutate(self, info: graphene.ResolveInfo) -> "SendConfirmationEmailMutation":
        AuthService.send_confirmation_email(info.context)
        return SendConfirmationEmailMutation(success=True)


class SendPasswordResetEmailMutation(graphene.Mutation):

    class Arguments:
        email = graphene.String(required=True)

    success = graphene.Boolean()

    @rate_limit("send_password_reset", limit=5, period_seconds=3600)
    def mutate(self, info: graphene.ResolveInfo, email: str):
        form = AuthService.send_password_reset_email(email)
        # Always report success to avoid leaking which emails are registered.
        return SendPasswordResetEmailMutation(success=True)


class Mutation(graphene.ObjectType):
    login = LoginMutation.Field()
    sign_up = SignUpMutation.Field()
    logout = LogoutMutation.Field()
    delete_account = DeleteAccountMutation.Field()
    send_confirmation_email = SendConfirmationEmailMutation.Field()
    send_password_reset_email = SendPasswordResetEmailMutation.Field()
