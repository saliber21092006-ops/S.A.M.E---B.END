from django.urls import path
from . import views

urlpatterns = [
    path("sign_up/", views.RegisterUser.as_view()),
]