import graphene

from main_app.graphql.user.types import ProfileType

from allauth.account.utils import complete_signup, perform_login, send_email_confirmation
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from allauth.account.forms import ResetPasswordForm
from allauth.account import app_settings as allauth_settings
from django.contrib.auth import logout, authenticate

from main_app.models.user import User
from main_app.util import require_auth
from main_app.validators import signup_validator

from ..error import MUError, MUErrorCode
    
class LoginMutation(graphene.Mutation):

    class Arguments:
        user = graphene.String()
        password = graphene.String()

    my_profile = graphene.Field(ProfileType)

    @classmethod
    def mutate(
        cls,
        root,
        info,
        user: str = None,
        password: str = None,
    ):
        is_email = "@" in user
        request = info.context
        
        profile = None
        if is_email:
            profile = authenticate(request, email=user, password=password)
        else:
            profile = authenticate(request, username=user, password=password)

        if profile is None:
            raise MUError(MUErrorCode.INVALID_LOGIN)
        
        perform_login(request, profile)
    
        return LoginMutation(
            my_profile = profile
        )        

class SignupMutation(graphene.Mutation):

    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    my_profile = graphene.Field(ProfileType)

    def mutate(
            self,
            info,
            username: str,
            email: str,
            password: str
    ):
        request = info.context
        
        signup_validator(username, email, password)

        user = get_adapter(request).new_user(request)
        user.username = username
        user.email = email
        user.set_password(password)
        user.save()

        if allauth_settings.EMAIL_VERIFICATION == allauth_settings.EmailVerificationMethod.MANDATORY:
            EmailAddress.objects.create(user=user, email=email, primary=True, verified=False)
        else:
            EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)

        complete_signup(request, user, allauth_settings.EMAIL_VERIFICATION, None)
        perform_login(request, user, allauth_settings.EMAIL_VERIFICATION)

        return SignupMutation(my_profile = user)

class LogoutMutation(graphene.Mutation):
    success = graphene.Boolean()

    def mutate(self, info):
        request = info.context
        logout(request)
        return LogoutMutation(success=True)
    
class DeleteAccountMutation(graphene.Mutation):
    success = graphene.Boolean()

    def mutate(self, info):
        request = info.context
        user: User = request.user
        if not user.id:
            raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)
        logout(request)
        user.delete()

        return DeleteAccountMutation(success = True)
    
class SendConfirmationEmailMutation(graphene.Mutation):
    success = graphene.Boolean()

    @require_auth
    def mutate(self, info):
        request = info.context
        send_email_confirmation(request, request.user)
        return SendConfirmationEmailMutation(success=True)
    
class SendPasswordResetEmailMutation(graphene.Mutation):
    success = graphene.Boolean()

    @require_auth
    def mutate(self, info):
        email = info.context.user.email
        form = ResetPasswordForm(data={"email": email})
        if form.is_valid():
            form.save(request=None)
        return SendPasswordResetEmailMutation(success=form.is_valid())

class Mutation(graphene.ObjectType):
    login = LoginMutation.Field()
    signup = SignupMutation.Field()
    logout = LogoutMutation.Field()
    delete_account = DeleteAccountMutation.Field()
    send_confirmation_email = SendConfirmationEmailMutation.Field()
    send_password_reset_email = SendPasswordResetEmailMutation.Field()

