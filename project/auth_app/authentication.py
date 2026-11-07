from rest_framework_simplejwt.authentication import JWTAuthentication

# authentiates the cookie from the frontend, since the frontend is not directly sending the token through authorization header, but through "credentials: inclue"
class JWTCookieAuthentication(JWTAuthentication):

    def authenticate(self, request):
        print("hit it!!!", request.COOKIES)
        raw_token = request.COOKIES.get('access')
        print("Raw token", raw_token)

        if raw_token is not None:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            return user, validated_token

        return super().authenticate(request)