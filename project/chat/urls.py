from django.urls import path
from . import views

urlpatterns = [
    path('chats/', views.ChatView.as_view()), # returns the chat lists of a user
    path('new-chat/', views.CreateChatID.as_view()), # creates a new chat and returns the new chat id
    path('messages/<uuid:chat_id>/', views.LoadMessagesView.as_view()), # returns the messages under a partcular chat
    path('streams/', views.ChatStreamView.as_view()), # endpoint for streaming messages 
    path('re-streams/', views.RegenerateChatStream.as_view()), # re genrates the last assistant response

    path('messages/', views.ChatMessagesView.as_view()),
    path('stream/', views.StreamChatView.as_view()),
]