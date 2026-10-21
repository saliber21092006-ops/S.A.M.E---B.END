from django.urls import path
from . import views

urlpatterns = [
    path('messages/', views.ChatMessagesView.as_view()),
    path('stream/', views.StreamChatView.as_view()),
]