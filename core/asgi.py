import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import core.routing

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(core.routing.websocket_urlpatterns)),
    }
)

# When using daphne to run server, it doesn't automatically server static files in debug mode.
from django.conf import settings

if settings.DEBUG:
    from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

    application = ASGIStaticFilesHandler(application)
