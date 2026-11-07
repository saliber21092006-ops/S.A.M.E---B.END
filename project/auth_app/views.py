from django.shortcuts import render
from rest_framework import generics
from .serializers import RegisterUserSerializer, UserSerializer
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny

# Create your views here.
class CookieTokenObtainPairView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username = username, password = password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            response = Response({"detail": "Login Successful"}, status=200)

            # access token 
            response.set_cookie(
                key='access',
                value=str(access),
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=3600,
                path='/'
            )

            # refresh token 
            response.set_cookie(
                key='refresh',
                value=str(refresh),
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=86400,
                path='/'
            )
            print(response)

            return response

        return Response({"detail": "Invalid Credentials, Try Again Please."}, status=401)


class CustomLogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh")
        if refresh_token:
            
            try:
                response = Response({"detail":"Logged out successfully"}, status=200)
                refresh = RefreshToken(refresh_token)
                refresh.blacklist()

            except Exception as e:
                return Response({"detail": "An error occured"}, status=401)

            finally:
                response.delete_cookie(key="access", path="/", samesite="Lax")
                response.delete_cookie(key="refresh", path="/", samesite="Lax")

            return response

# class RegisterUser(generics.CreateAPIView):
#     serializer_class = RegisterUserSerializer
#     queryset = User.objects.all()


class RegisterUser(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        email = data.get('email', '')
        username = data.get('username', '')
        password = data.get('password', '')

        if not email or not username or not password:
            return Response({'detail': 'All fields are required'}, status=400)

        if User.objects.filter(email = email).exists() or User.objects.filter(username = username).exists():
            return Response({'detail': 'Username or Email already exist. Please try another.'}, 400)

        user = RegisterUserSerializer(data = data)
        if user.is_valid():
            user.save()

            # get newly created user 
            newly_created_user = User.objects.get(username=username)

            # After Successfully Creating User Account, Automatically Login
            refresh = RefreshToken.for_user(newly_created_user)
            access = refresh.access_token

            response = Response({'detail': 'Account Created successfully, and Login Successful!'}, status=201)
            # Then we set the access token >>
            response.set_cookie(
                key='access',
                value=str(access),
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=3600,
                path='/'
            )
            # the refresh token >>>
            response.set_cookie(
                key='refresh',
                value=str(refresh),
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=84600,
                path='/'
            )

            return response
        return Response(user.errors, status=400)

# CVB that returns the user's info ->
class Get_user_info(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = User.objects.get(id = self.request.user.id)
        serializer = UserSerializer(queryset, many = False)
        return Response(serializer.data, status=200)