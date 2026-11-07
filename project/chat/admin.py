from django.contrib import admin
from .models import ChatModel, Chat, Message, MessageAttachment

# Register your models here.
admin.site.register(ChatModel)

admin.site.register(Chat)
admin.site.register(Message)
admin.site.register(MessageAttachment)