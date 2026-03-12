"""
URL configuration for moveus project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.http import HttpRequest
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from .settings import DEBUG


class CustomGraphQLView(GraphQLView):
    def get_context(self, request: HttpRequest, *args, **kwargs) -> HttpRequest:
        # Try to get the session token from the header.
        authorization_header = request.headers.get("authorization")
        if authorization_header:
            token = request.headers.get("authorization").split()[1]
            if token:
                try:
                    # Retrieve the session corresponding to the token.
                    session = Session.objects.get(session_key=token)
                    # Optionally, set request.session to the decoded session data.
                    request.session = session.get_decoded()
                    # If the session contains a user id, fetch the user.
                    user_id = request.session.get("_auth_user_id")
                    if user_id:
                        request.user = get_user_model().objects.get(pk=user_id)
                except Session.DoesNotExist:
                    pass  # Or handle invalid token appropriately.

        return super().get_context(request, *args, **kwargs)

    @staticmethod
    def format_error(error) -> dict:
        formatted_error = super(CustomGraphQLView, CustomGraphQLView).format_error(
            error
        )

        try:
            formatted_error["error_code"] = error.original_error.code
        except AttributeError:
            pass

        return formatted_error


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),
    path("graphql", csrf_exempt(CustomGraphQLView.as_view(graphiql=DEBUG))),
]
