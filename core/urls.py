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

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.http import HttpRequest, HttpResponseForbidden
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from .settings import DEBUG


class CustomGraphQLView(GraphQLView):
    def dispatch(self, request: HttpRequest, *args, **kwargs):
        # CSRF defense-in-depth: with csrf_exempt the GraphQL view doesn't run
        # Django's CSRF middleware, so reject any cross-origin browser request
        # whose Origin isn't on our allow-list. Requests without an Origin
        # header (curl, server-to-server, same-origin GETs in some browsers)
        # are left alone.
        origin = request.headers.get("origin")
        if origin and origin not in settings.CORS_ALLOWED_ORIGINS:
            return HttpResponseForbidden("Origin not allowed")
        return super().dispatch(request, *args, **kwargs)

    def get_context(self, request: HttpRequest, *args, **kwargs) -> HttpRequest:
        token = self._extract_session_token(request)
        if token:
            try:
                session = Session.objects.get(session_key=token)
                request.session = session.get_decoded()
                user_id = request.session.get("_auth_user_id")
                if user_id:
                    request.user = get_user_model().objects.get(pk=user_id)
            except Session.DoesNotExist:
                pass

        return super().get_context(request, *args, **kwargs)

    @staticmethod
    def _extract_session_token(request: HttpRequest) -> str | None:
        header = request.headers.get("authorization", "")
        parts = header.split()
        # Accept "Session <id>" or "Bearer <id>" or bare "<id>".
        if len(parts) == 2:
            return parts[1]
        if len(parts) == 1:
            return parts[0]
        return None

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
