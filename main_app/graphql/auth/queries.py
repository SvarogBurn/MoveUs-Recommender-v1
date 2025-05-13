import graphene

from main_app.models.user import User


class AuthUtilQuery(graphene.ObjectType):
    username_taken = graphene.Boolean(
        username = graphene.String(),
        required = True
        )
    
    email_taken = graphene.Boolean(
        email = graphene.String(),
        required = True
        )
    
    is_logged_in = graphene.Boolean()
    
    def resolve_username_taken(self, info, username: str):
        if User.objects.filter(username=username).count():
            return True
        return False

    def resolve_email_taken(self, info, email: str):
        if User.objects.filter(email=email).count():
            return True
        return False
    
    def resolve_is_logged_in(self, info):
        return bool(info.context.user)