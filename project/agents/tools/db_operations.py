"""Tools to carry out database operations"""
import traceback

from chat.models import Chat, Message
from chat.serializers import MessageSerializer

class DBOperation:
    def __init__(self, query, user=None):
        self.query = query
        self.user = user

    def search_chat_conversations(self, chat_id):
        """Filters conversation in a chat using keywords"""
        if not self.query:
            raise ValueError("Query cannot be empty")

        try:
            # get the chat 
            chat = Chat.objects.get(id=chat_id, user=self.user)
            messages = Message.objects.filter(chat=chat, content__icontains=self.query).order_by("-timestamp")

            if messages:
                serializer = MessageSerializer(messages, many=True)
                return serializer.data

        except Exception:
            traceback.print_exc()
            return {
                "success": False,
                "output": None,
                "error": "An error occured"
            }

