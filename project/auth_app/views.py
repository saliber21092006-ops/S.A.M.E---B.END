from django.shortcuts import render
from rest_framework import generics
from .serializers import RegisterUserSerializer, UserSerializer
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.
class CookieTokenObtainPairView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username = username, password = password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            response = Response({"detail": "Login Successful"})

            # access token 
            response.set_cookie(
                key='access',
                value=str(access),
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=2,
                path='/'
            )

            # refresh token 
            response.set_cookie(
                key='refresh',
                value=str(refresh),
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=7,
                path='/'
            )

            return response

        return Response({"detail": "Invalid Credentials"}, status=200)


class RegisterUser(generics.CreateAPIView):
    serializer_class = RegisterUserSerializer
    queryset = User.objects.all()

# CVB that returns the user's info ->
class Get_user_info(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = User.objects.get(id = self.request.user.id)
        serializer = UserSerializer(queryset, many = False)
        return Response(serializer.data, status=200)