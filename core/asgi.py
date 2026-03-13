import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import core.routing

http_application = get_asgi_application()

# When using daphne to run server, it doesn't automatically serve static files in debug mode.
# Only wrap HTTP with ASGIStaticFilesHandler — wrapping WebSocket causes shutdown timeouts.
from django.conf import settings

if settings.DEBUG:
    from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

    http_application = ASGIStaticFilesHandler(http_application)

application = ProtocolTypeRouter(
    {
        "http": http_application,
        "websocket": AuthMiddlewareStack(URLRouter(core.routing.websocket_urlpatterns)),
    }
)
