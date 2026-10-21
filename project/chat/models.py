from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class ChatModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_user")
    role = models.CharField(max_length=200, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.role == "user":
            return f"{self.user.username}: {self.content[:5]} >>> "
        return f"[{self.user.username}] Assistant: {self.content[:20]}...."