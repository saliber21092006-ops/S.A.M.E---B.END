from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.CookieTokenObtainPairView.as_view()),
    path("sign_up/", views.RegisterUser.as_view()),
    path("get_user_info/", views.Get_user_info.as_view()),
]