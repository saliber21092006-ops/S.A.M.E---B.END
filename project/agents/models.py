from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

# Create your models here.
class AgentMemory(models.Model):
    CATEGORY_CHOICES = [
        ("preference", "Preference"), ("skill", "Skill"), ("project", "Project"),
        ("instruction", "Instruction"), ("personal", "Personal"), ("general", "General")
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agent_memories")
    content = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="general")
    importance = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # model_name_plural = "Agent Memories"
        ordering = ["-importance", "-updated_at"]
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'is_active'])
        ]

    def __str__(self):
        return f"{self.user.username} - {self.category}: {self.content[:50]}"