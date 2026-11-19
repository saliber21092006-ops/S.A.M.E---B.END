from rest_framework.views import APIView
from agents import (orchestrator, registry, planner, executor, llm, memory_manager)
import os, mimetypes, uuid, logging, ollama
from django.http import StreamingHttpResponse
from .models import Chat, Message, MessageAttachment
from .serializers import MessageSerializer, MessageAttachmentSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404

from agents import (llm, planner, executor, orchestrator, registry, memory_manager)
from agents.tools import basic_math, web_scraper


logger = logging.getLogger(__name__)

_llm = llm.Oll_LLM()
_registry = registry.ToolRegistry()
_memory_manager = memory_manager.MemoryManager(llm=_llm)

# ================== TOOL REGISTRATION ======================
_registry.register(
    name="add_numbers",
    description="Adds two numbers",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "required": ["a", "b"],
        "additionalProperties": False
    },
    function=basic_math.add_numbers
)

_registry.register(
    name="multiply_numbers",
    description="Multiplies two numbers",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "required": ["a", "b"],
        "additionalProperties": False
    },
    function=basic_math.multiply_numbers
)

_registry.register(
    name="divide_numbers",
    description="Divides two numbers",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "required": ["a", "b"],
        "additionalProperties": False
    },
    function=basic_math.divide_numbers
)

_registry.register(
    name="search_and_scrape",
    description="Searches the web for a query, scrapes the top results, and returns formatted context",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "num_results": {"type": "number"}
        },
        "required": ["query", "num_results"],
        "additionalProperties": False
    },
    function=web_scraper.search_and_scrape
)

_registry.register(
    name="scrape_url",
    description="Fetches a webpage and extracts clean, readable text.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
        },
        "required": ["url"],
        "additionalProperties": False
    },
    function=web_scraper.scrape_url
)

# ==================== TOOL REGISTRATION ======================

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

def summarize_first_message(first_message) -> str:
    system_prompt = """
        You are a chat title summarizer for Socratic AI Math Engine (SAME), a chat app. 
        Your job is to summarize the message of a user in not more than 5 words.

        Example:

        User: Hello!
        You: Casual greeting.  
    """

    full_messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": first_message
        }
    ]

    print(f"[SUMMARIZER] summarizing '{first_message}'")
    ai = ollama.chat(
        model="qwen2.5:1.5b",
        messages=full_messages,
        stream=False,
        think=False
    )

    return ai['message']['content']


class ChatStreamView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        content = request.data.get("content", "")
        content = str(content).strip()

        _executor = executor.ToolExecutor(registry=_registry)
        _planner = planner.AgentPlanner(llm=_llm, registry=_registry)
        _agent = orchestrator.AgentOrchestrator(planner=_planner, executor=_executor, memory_manager=_memory_manager, max_steps=5)

        print("[ALL CONTENT]", content)

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
                    title = summarize_first_message(content)
                    chat = Chat.objects.create(user = self.request.user, title = title if title else "New Conversation")
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

            # try:
            #      # Run the agent 
            #     print("[STREAMER] Starting agent response stream...")
            #     agent_result = _agent.run(messages=history, user=self.request.user)
            #     print("[AGENT RESPONSE]", agent_result)
    
            #     # check if the agent completed successfully 
            #     if not agent_result["success"]:
            #         raise RuntimeError(
            #             agent_result["error"] or agent_result["response"]
            #             or "The agent failed to generate a response. Please try again."
            #         )

            #     # get final response from the agent 
            #     agent_response = agent_result['response']

            #     if not agent_response:
            #         raise RuntimeError("The agent returned an empty response, or did not return a response. Please try again.")
                            
            #     # Temporarily send the completed response as one chunk
            #     full_response = str(agent_response)
            #     yield full_response

            #     # for chunk in ai_response_generator(history):
            #     # for chunk in ai_response_generator(agent_result['response']):
            #     #     if not chunk:
            #     #         continue
            #     #     full_response += chunk
            #     #     yield chunk
             
            try:
                print("[STREAMER] Starting agent streaming response...")
                print(f"\n[MSG HISTORY] {history}")

                for chunk in _agent.stream(messages=history, user=self.request.user):
                    if not chunk:
                        continue
                    full_response += chunk
                    yield chunk
                
                print("[STREAMER] Agent streaming completed")

            except Exception:
                logger.exception("Agent streaming error")

                if not full_response:
                    error_message = ("Sorry, something went wrong while processing your request. Please try again.")
                    full_response += error_message
                    yield error_message

            finally:
                # save the response or partial response if interrupted
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

