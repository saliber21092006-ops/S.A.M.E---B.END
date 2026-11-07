from rest_framework import serializers
from auth_app.serializers import UserSerializer
from .models import ChatModel, Chat, Message, MessageAttachment

class ChatModelSerializer(serializers.ModelSerializer):
    user = UserSerializer(write_only = True)

    class Meta:
        model = ChatModel
        fields = ['id', 'user', 'role', 'content', 'timestamp']
        ordering = ('-timestamp')

class MessageAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MessageAttachment
        fields = ['id', 'original_name', 'file', 'url', 'file_size', 'mime_type', 'attachment_type', 'uploaded_at']
        read_only_fields = ["id", "file_size", "uploaded_at"]

    def get_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url

        if request:
            return request.build_absolute_uri(url)
        return url


class MessageSerializer(serializers.ModelSerializer):
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender', 'role', 'content', 'message_type', 'attachments', 'timestamp', 'updated_at', 'is_edited']
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at', 'is_edited']


class ChatSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many = True, read_only = True)

    class Meta:
        model = Chat
        fields = ['id', 'title', 'created_at', 'updated_at', 'messages',]
        read_only_fields = ['id', 'created_at', 'updated_at']
