from rest_framework import serializers
from auth_app.serializers import UserSerializer
from .models import ChatModel

class ChatModelSerializer(serializers.ModelSerializer):
    user = UserSerializer(write_only = True)

    class Meta:
        model = ChatModel
        fields = ['user', 'role', 'content', 'timestamp']
        ordering = ('-timestamp')