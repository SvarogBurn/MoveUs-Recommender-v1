class SessionCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if 'sessionid' in response.cookies:
            cookie = response.cookies['sessionid']
            cookie['httponly'] = False 
            cookie['samesite'] = 'Lax'
            cookie['secure'] = False

        return response
