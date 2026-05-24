from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class SessionCookieMiddleware:
    """Dev-only: strip HttpOnly from the sessionid cookie so the web frontend
    can read it via document.cookie and forward it as `Authorization: Session
    <id>` on subsequent requests. In production, Django's default cookie flags
    apply (HttpOnly + Secure) and the browser auto-attaches the cookie on
    same-site requests; this middleware is not registered there.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if "sessionid" in response.cookies:
            cookie = response.cookies["sessionid"]
            cookie["httponly"] = False
            cookie["secure"] = False
        return response
