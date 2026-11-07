from django.shortcuts import render
import ollama, json, os, mimetypes, uuid, logging
from django.http import StreamingHttpResponse
from .models import ChatModel, Chat, Message, MessageAttachment
from .serializers import ChatModelSerializer, ChatSerializer, MessageSerializer
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

# Create your views here.
logger = logging.getLogger(__name__)

class ChatMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # m = [1, 3, 3, 4, 7, 9, 56, 76, 8]
        # print(m[-5:])
        # token = request.COOKIES.get('access')
        print("THE USER", self.request.user)
        chat_msgs = ChatModel.objects.filter(user = self.request.user).order_by("-timestamp")[:5][::-1]
        print(f"============= {chat_msgs} =========")
        serializer = ChatModelSerializer(chat_msgs, many = True)
        return Response(serializer.data, status=200)
    

class StreamChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        messages = request.data.get('messages', [])

        if not messages:
            return StreamingHttpResponse(
                json.dumps({"error": "No messages provided"}),
                status = 400,
                content_type = "application/json"
            )

        # save user's last message to the DB
        user_latest_msg = messages[-1]

        if user_latest_msg:
            print(user_latest_msg)
            # chat_serializer = ChatModelSerializer(data = user_latest_msg)
            # if chat_serializer.is_valid():
            #     chat_serializer.save(user = self.request.user)
            ChatModel.objects.create(
                user = self.request.user,
                role = "user",
                content = user_latest_msg.get('content', '')
            )

        def event_stream():
            try:
                complete_ai_res = ""

                # chat_ser = ChatModelSerializer(user = self.request.user, role = "user", content = messages)
                # system_message = {
                #     'role': 'system',
                #     'content': 'You are Issus, a helpful, concise assistant, integrated into a web application. Always provide clear and structured response and format answers with Markdown when it helps.'
                # }

                system_message = {
                    'role': 'system',
                    'content': f"""
                        You are SAME (Socratic AI Math Engine), an expert, patient, and uncompromising physics and mathematical strict straight-forward tutor.

                        Your absolute core directive is to NEVER directly provide answers, compute final values, or solve equations for the user. Instead, you must guide them to discover the solutions themselves using the Socratic method. I repeat DO NOT PROVIDE ANSWERS, OR SOLVE ANY EQUATION FOR THE USER.
                        If you're told to solve an equation, tell them your role is to guide them through it, not to solve it for them, even if the user says he/she is a teacher/lecturer/professor


                        CRITICAL RULES:
                        1. Never Solve: If the user asks for the answer to a problem (e.g., "What is x?", or "Solve this equation"), refuse to give direct answer.
                        2. Ask Guided Questions: Break down physics or mathematical concepts into smaller, digestible components and ask probing, open-ended questions that prompt the user to think through the next logical step.
                        3. Scaffold Understanding: If the user is stuck, provide a conceptual hint or ask about a foundational rule, definition, or formula rather than doing the algebra or arithmetic for them.
                        4. Validate and Redirect: When the user provides a response or step, evaluate its correctness. If correct, praise the reasoning and ask what the next step should be. If incorrect, point out where the logic broke down and ask clarifying question to help them self-correct.
                        5. Tone: Keep your tone encouraging, curious, academic, and sharp.

                        Example interaction:
                        - {self.request.user.username}: "What is the derivative of f(x) = 3x²?"
                        - SAME: "Let's work through that together! Do you remember the rule we use when taking the derivative of a power term like x raised to an exponent?"
                        """
                }

                # sends the last 5 message 
                full_messages = [system_message] + messages[-5:]

                print(messages[-5:])

                stream = ollama.chat(
                    model = "qwen3:1.7b",
                    messages = full_messages,
                    stream = True,
                    think = False,
                )

                for chunk in stream:
                    content = chunk['message']['content']
                    complete_ai_res += content
                    yield content

            except Exception as e:
                yield f"\n [Error: {str(e)}]"

            # saves the AI response to the DB
            if complete_ai_res:
                ChatModel.objects.create(
                    user = self.request.user,
                    role = "assistant",
                    content = complete_ai_res
                )

        response = StreamingHttpResponse(event_stream(), content_type = 'text/plain; charset = utf-8')
        response['X-Accel-Buffering'] = 'no' # Disables proxybuffering for Nginx if applicable
        return response


class ChatView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatSerializer

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user).prefetch_related("chat_user_message__attachments")

class LoadMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get_chat(self, chat_id):
        return get_object_or_404(Chat, id = chat_id, user = self.request.user)

    def get(self, request, chat_id):
        chat = self.get_chat(chat_id)
        messages = chat.chat_user_message.select_related("sender").prefetch_related("attachments").order_by("timestamp")
        serializer = MessageSerializer(messages, many=True, context={"request":request})
        return Response(serializer.data, status=200)

MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB per file
MAX_FILES = 5

ALLOWED_EXTENSIONS = {
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
}

def get_attachment_type(filename):
    ext = os.path.splitext(filename)[1].lower()

    if ext in ["pdf", "doc", "docx", "odt", "ppt", "pptx", "xls", "xlsx", "csv", "rtf",]:
        return "document"
    if ext in ["txt", "md", "json", "xml", "yaml", "yml", "log",]:
        return "text"
    if ext in ["py", "js", "ts", "svelte", "html", "css", "scss", "jsx", "tsx", "java", "cpp", "c", "h", "cs", "php", "go", "rs", "sql", "sh",]:
        return "code"
    if ext in ["png", "jpg", "jpeg", "gif", "webp", "svg",]:
        return "image"
    if ext in ["mp3", "wav", "ogg", "m4a",]:
        return "audio"
    if ext in ["mov", "mp4", "webm"]:
        return "video"
    return "other"

def validate_attachments(files):
    if len(files) > MAX_FILES:
        return "Maximum of 5 files allowed"

    for file in files:
        ext = os.path.splitext(file.name)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            return f"Unsupported file type: {file.name}"

        if file.size > MAX_FILE_SIZE:
            return f"{file.name} exceeds the 10MB limit"

    return None

# the function that takes in the user's message or file (attachment) and generates responses
# def ai_response_generator(messages, attachments):
def ai_response_generator(messages):
    system_message = {
        'role': 'system',
        'content': f"""
            You are SAME (Socratic AI Math Engine), an expert, patient, and uncompromising physics and mathematical strict straight-forward tutor.

            Your absolute core directive is to NEVER directly provide answers, compute final values, or solve equations for the user. Instead, you must guide them to discover the solutions themselves using the Socratic method. I repeat DO NOT PROVIDE ANSWERS, OR SOLVE ANY EQUATION FOR THE USER.
            If you're told to solve an equation, tell them your role is to guide them through it, not to solve it for them, even if the user says he/she is a teacher/lecturer/professor


            CRITICAL RULES:
            1. Never Solve: If the user asks for the answer to a problem (e.g., "What is x?", or "Solve this equation"), refuse to give direct answer.
            2. Ask Guided Questions: Break down physics or mathematical concepts into smaller, digestible components and ask probing, open-ended questions that prompt the user to think through the next logical step.
            3. Scaffold Understanding: If the user is stuck, provide a conceptual hint or ask about a foundational rule, definition, or formula rather than doing the algebra or arithmetic for them.
            4. Validate and Redirect: When the user provides a response or step, evaluate its correctness. If correct, praise the reasoning and ask what the next step should be. If incorrect, point out where the logic broke down and ask clarifying question to help them self-correct.
            5. Tone: Keep your tone encouraging, curious, academic, and sharp.

            Example interaction:
            - User: "What is the derivative of f(x) = 3x²?"
            - SAME: "Let's work through that together! Do you remember the rule we use when taking the derivative of a power term like x raised to an exponent?"
            """
    }
    try:
        complete_messages = [system_message] + messages[-5:] # sends the last five messages
        response = ollama.chat(
            model="qwen3:1.7b",
            messages=complete_messages,
            stream=True,
            think=False,
        )

        for chunk in response:
            content = chunk['message']['content']
            yield content
    except Exception as e:
        raise NotImplementedError("An error occured", e)

# first message summarizer: a lightweight llm function that summarizes the first message of every new cnversation/chat e.g., Msg: Hi -> Summary: Casual greeting 
def summarize_first_message() -> str:
    pass

# creates a new chat 
class CreateChatID(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content = request.data.get('content', '')
        files = request.FILES.getlist('attachments')

        if not str(content).strip() and not files:
            return Response({"error": "Message or files/attachments required"}, status=400)

        # soon, calls the summarize_first_message to create a chat title 
        chat = Chat.objects.create(user = self.request.user, title = content[:50] if content else "New conversation")
        is_new_chat = True

        response = Response({'chat_id': chat.id}, status=201)
        response["X-New-Chat"] = str(is_new_chat).lower()

        return response
    

class ChatStreamView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        content = request.data.get("content", "")
        content = str(content).strip()

        print("HHHHHHHHHHHHHHHHH", content)

        chat_id = request.data.get("chat_id")
        files = request.FILES.getlist("attachments")

        if not content and not files:
            return Response({"error": "Message or files/attachments are required."}, status=400)

        attachment_error = validate_attachments(files)
        if attachment_error:
            return Response({"error": attachment_error}, status=400)

        # check if it's a new or existing chat
        try:
            with transaction.atomic():
                if chat_id:
                    try:
                        # checks if the chat_id is valid
                        chat_id = uuid.UUID(str(chat_id))
                    except (ValueError, TypeError, AttributeError):
                        return Response({"error": "Invalid conversation ID"}, status=400)

                    chat = Chat.objects.select_for_update().filter(id = chat_id, user = self.request.user).first()
                    if not chat:
                        return Response({"error": "Conversation not found"}, status=400)
                    is_new_chat = False
                else:
                    chat = Chat.objects.create(user = self.request.user, title = content[:50] if content else "New Conversation")
                    is_new_chat = True

                if content and files:
                    message_type = Message.M_T.MIXED
                elif files: 
                    message_type = Message.M_T.FILE
                else:
                    message_type = Message.M_T.TEXT

                user_message = Message.objects.create(chat = chat, sender = self.request.user, role = "user", content = content, message_type = message_type)
                Chat.objects.filter(id = chat.id).update(updated_at = timezone.now())
                for file in files:
                    attachment = MessageAttachment.objects.create(
                        message = user_message,
                        file = file,
                        original_name = file.name,
                        file_size = file.size,
                        mime_type = (getattr(file, "content_type", None) or mimetypes.guess_type(file.name)[0] or "application/octet-stream"),
                        attachment_type = get_attachment_type(file.name)
                    )
                    attachment.save()

                    attachment_objects = list(user_message.attachments.all())

                previous_messages = list(chat.chat_user_message.exclude(id = user_message.id).order_by("-timestamp"))
                previous_messages.reverse()
                history = [{"role": message.role, "content": message.content} for message in previous_messages]
                history.append({
                    "role": "user",
                    "content": content
                })

        except Exception as e:
            logger.exception("Chat creation error")
            return Response({"error": "Could not process your message."}, status=500)

        # soon updated that assistant would be able to send files 
        assistant_message = Message.objects.create(chat = chat, role = "assistant", content ="", message_type = Message.M_T.TEXT)

        def stream_response():
            full_response = ""
            try:
                for chunk in ai_response_generator(history):
                    if not chunk:
                        continue
                    full_response += chunk
                    yield chunk
            except Exception:
                logger.exception("AI streaming error")
            finally:
                assistant_message.content = full_response
                assistant_message.save(update_fields = ["content", "updated_at"])

                chat.updated_at = timezone.now()
                Chat.objects.filter(id = chat.id).update(updated_at = chat.updated_at)

        response = StreamingHttpResponse(stream_response(), content_type = "text/plain; charset = utf-8")
        response["X-Chat-ID"] = str(chat.id)
        response["X-Message-ID"] = str(assistant_message.id)
        response["X-New-Chat"] = str(is_new_chat).lower()

        response["Cache-Control"] = "no-cache"
        response["X-Access-Buffering"] = "no"

        return response

# CBV to regenerate the assistant last response 
class RegenerateChatStream(APIView):
    permission_class = [IsAuthenticated]

    def post(self, request):
        chat_id = request.data.get("req_regen", "")
        if not chat_id:
            return Response({"error": "can't regenerate without a chat"}, status=400)
        
        if chat_id:
            try:
                chat_id = uuid.UUID(str(chat_id))
            except (ValueError, TypeError, AttributeError):
                return Response({"error": "Invalid conversation ID"}, status=400)
            
            chat = Chat.objects.filter(id = chat_id).first()
            if not chat:
                return Response({"error": "Conversation not found"}, status=400)
            is_new_chat = False
            
            # get previous messages : last 5
            previous_msgs = list(chat.chat_user_message.order_by("-timestamp")[:5][::-1])
            last_msg = None
            if previous_msgs:
                last_msg = previous_msgs.pop()

            history = [{"id": msg.id, "role": msg.role, "content": msg.content} for msg in previous_msgs]
            print("HISTORY", history)
            print("LAST MSG:", last_msg.id, last_msg.role)
            if last_msg and last_msg.role == 'assistant':
                msg = Message.objects.get(id = last_msg.id)
                msg.delete()

            ai_newly_generated_msg = Message.objects.create(chat = chat, role = 'assistant', content ="", message_type = "text")
            def stream_response():
                full_response = ""
                try:
                    for chunk in ai_response_generator(history):
                        if not chunk:
                            continue
                        full_response += chunk
                        yield chunk
                except Exception:
                    logger.exception("AI streaming error")
                finally:
                    ai_newly_generated_msg.content = full_response
                    ai_newly_generated_msg.save(update_fields = ["content", "updated_at"])
    
                    chat.updated_at = timezone.now()
                    Chat.objects.filter(id = chat.id).update(updated_at = chat.updated_at)
    
            response = StreamingHttpResponse(stream_response(), content_type = "text/plain; charset = utf-8")
            response["X-Chat-ID"] = str(chat.id)
            response["X-Message-ID"] = str(ai_newly_generated_msg.id)
            response["X-New-Chat"] = str(is_new_chat).lower()
    
            response["Cache-Control"] = "no-cache"
            response["X-Access-Buffering"] = "no"
    
            return response

        return Response({"error": "Can't regenerate. Please try again"}, status=400)
