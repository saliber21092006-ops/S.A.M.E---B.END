from django.shortcuts import render
from rest_framework import generics
from .serializers import RegisterUserSerializer
from django.contrib.auth.models import User

# Create your views here.
class RegisterUser(generics.CreateAPIView):
    serializer_class = RegisterUserSerializer
    queryset = User.objects.all()