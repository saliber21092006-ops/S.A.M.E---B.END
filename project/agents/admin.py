from django.contrib import admin
from .models import AgentMemory

# Register your models here.
@admin.register(AgentMemory)
class AgentModelAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'importance', 'is_active', 'created_at')
    list_filter = ('category', 'importance', 'is_active')
    search_fields = ('user__username', 'content')
    readonly_fields = ('created_at', 'updated_at')