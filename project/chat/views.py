from django.shortcuts import render
import ollama, json
from django.http import StreamingHttpResponse
from .models import ChatModel
from .serializers import ChatModelSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Create your views here.
class ChatMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        chat_msgs = ChatModel.objects.filter(user = self.request.user)
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

        def event_stream():
            try:
                # chat_ser = ChatModelSerializer(user = self.request.user, role = "user", content = messages)
                # system_message = {
                #     'role': 'system',
                #     'content': 'You are Issus, a helpful, concise assistant, integrated into a web application. Always provide clear and structured response and format answers with Markdown when it helps.'
                # }

                system_message = {
                    'role': 'system',
                    'content': """
                        You are SAME (Socratic AI Math Engine), an expert, patient, and uncompromising physics and mathematical tutor.

                        Your absolute core directive is to NEVER directly provide answers, compute final values, or solve equations for the user. Instead, you must guide them to discover the solutions themselves using the Socratic method.

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

                full_messages = [system_message] + messages

                print(messages)

                stream = ollama.chat(
                    model = "qwen3:1.7b",
                    messages = full_messages,
                    stream = True,
                    think = False,
                )

                for chunk in stream:
                    content = chunk['message']['content']
                    yield content

            except Exception as e:
                yield f"\n [Error: {str(e)}]"

        response = StreamingHttpResponse(event_stream(), content_type = 'text/plain; charset = utf-8')
        response['X-Accel-Buffering'] = 'no' # Disables proxybuffering for Nginx if applicable
        return response