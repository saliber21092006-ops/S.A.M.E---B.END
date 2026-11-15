from .models import AgentMemory

class MemoryEngine:
    def save(self, user, content, category="general", importance=3):
        # validate the content 
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Memory content cannot be empty")
        content = content.strip()

        # validate the category 
        valid_categories = dict(AgentMemory.CATEGORY_CHOICES)
        if category not in valid_categories:
            raise ValueError(f"Invalid memory category: {category}")

        # validate the importance 
        if (isinstance(importance, bool) or not isinstance(importance, int) or not 1 <= importance <= 5):
            raise ValueError("Importance must be between 1 and 5")

        # save or update an existing memory 
        memory, created = AgentMemory.objects.update_or_create(
            user=user,
            content=content,
            defaults={
                "category": category,
                "importance": importance,
                "is_active": True
            }
            )
        return memory

    def retrieve(self, user, category=None, limit=10):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("Limit must be a positive integer")
        memories = AgentMemory.objects.filter(user=user, is_active=True)

        if category:
            memories = memories.filter(category=category)
        return memories.order_by("-importance", "-updated_at")[:limit]

    def search(self, user, query, limit=10):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query cannot be empty")

        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("Limit must be a positive integer")

        return AgentMemory.objects.filter(user=user, is_active=True, content__icontains=query.strip()).order_by("-importance", "-updated_at")[:limit]

    def update(self, user, memory_id, **changes):
        allowed_fields = {
            "content",
            "category",
            "importance"
        }

        if not changes:
            raise ValueError("No changes provided")

        if not set(changes).issubset(allowed_fields):
            raise ValueError("Invalid memory field")

        memory = AgentMemory.objects.filter(id=memory_id, user=user, is_active=True).first()
        if memory is None:
            raise AgentMemory.DoesNotExist("Memory not found")

        if "content" in changes:
            content = changes["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Memory content cannot be empty")
            memory.content = content.strip()

        if "category" in changes:
            category = changes["category"]
            if category not in dict(AgentMemory.CATEGORY_CHOICES):
                raise ValueError("Invalid memory category")
            memory.category = category

        if "importance" in changes:
            importance = changes["importance"]
            if (isinstance(importance, bool) or not isinstance(importance, int) or not 1 <= importance <= 5):
                raise ValueError("Importance must be between 1 and 5")
            memory.importance = importance

        memory.save()
        return memory

    def deactivate(self, user, memory_id):
        memory = AgentMemory.objects.filter(id=memory_id, user=user, is_active=True).first()
        if memory is None:
            return False
        memory.is_active = False
        memory.save(update_fields=["is_active", "updated_at"])

        return True