from django.db import models
from django.contrib.auth.models import User
import uuid, os
from django.core.validators import FileExtensionValidator

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


class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_chat")
    title = models.CharField(max_length = 100, default="New Conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} - {self.id}"


class Message(models.Model):
    class M_T(models.TextChoices):
        TEXT = "text", "Text"
        FILE = "file", "File"
        MIXED = "mixed", "Text and Files"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="chat_user_message")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="chat_messages")
    role = models.CharField(max_length=200, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=20, choices=M_T)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_updated = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]

    # def save(self, *args, **kwargs):
    #     if self.pk:
    #         self.is_edited = True

    #     super().save(*args, **kwargs)

    #     # update the parent conversation timestamp
    #     Chat.objects.filter(pk=self.chat_id).update(updated_at = self.timestamp)

    def __str__(self):
        if self.role == "user":
            return f"{self.chat.user.username}: {self.content[:10]} >>> "
        return f"{self.chat.user.username} >> {self.chat.id} >> {self.role} >> {self.content[:20]}...."


def attachment_upload_path(instance, filename):
    # this function organize files by chat and message 
    extension = os.path.splitext(filename)[1].lower()

    return (
        f"chat_attachments/{instance.message.chat_id}/{instance.message.id}/{uuid.uuid4().hex}{extension}"
    )


class MessageAttachment(models.Model):
    class AttachmentType(models.TextChoices):
        IMAGE = "image", "Image"
        DOCUMENT = "document", "Document"
        CODE = "code", "Code"
        AUDIO = "audio", "Audio"
        VIDEO = "video", "Video"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to=attachment_upload_path,
        validators=[
            FileExtensionValidator(allowed_extensions=[
                # Documents
                "pdf", "doc", "docx", "odt", "ppt", "pptx", "xls", "xlsx", "csv", "rtf",
                # Texts
                "txt", "md", "json", "xml", "yaml", "yml", "log",
                # Codes 
                "py", "js", "ts", "svelte", "html", "css", "scss", "jsx", "tsx", "java", "cpp", "c", "h", "cs", "php", "go", "rs", "sql", "sh",
                # Images 
                "png", "jpg", "jpeg", "gif", "webp", "svg",
                # Audio 
                "mp3", "wav", "ogg", "m4a",
                # Video 
                "mov", "mp4", "webm"
            ])
        ]
    )
    original_name = models.CharField(max_length=250)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=150, blank=True)
    attachment_type = models.CharField(max_length=20, choices=AttachmentType.choices, default=AttachmentType.OTHER)

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name