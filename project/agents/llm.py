"""COMMUNICATES DIRECTLY TO THE MODEL: QWEN3:1.7B"""
# import requests
import ollama

# class OllamaLLM:
#     def __init__(self, model = "qwen3:1.7b", bas_url = "http://localhost:11434"):
#         self.model = model 
#         self.base_url = bas_url.strip("/")

#     def generate(self, messages, temperature = 0.7):
#         print("generating....")
#         url = f"{self.base_url}/api/chat"
#         system_message = ""
#         payload = {
#             "model": self.model,
#             "messages": messages,
#             "stream": False, 
#             "options": {
#                 "temperature": temperature
#             }
#         }

#         try:
#             response = requests.post(url, json = payload, timeout = 180)
#             response.raise_for_status()

#             data = response.json()
#             return data['message']['content']
        
#         except requests.exceptions.ConnectionError:
#             raise Exception("Cannot connect to ollama, ensure ollama is running.")

#         except requests.exceptions.Timeout:
#             raise Exception("Ollama took too long to respond")

#         except requests.exceptions.HTTPError as e:
#             raise Exception(f"Ollama HTTP error: {e}")


class Oll_LLM():
    def __init__(self, model = "qwen3:1.7b"):
        self.model = model

    def generate(self, messages):
        """Generates a complete response (used for planning and memory)"""
        # print(messages)
        try:
            if not messages:
                raise ValueError("Messages can't be blank")

            print("[LLM] GENERATING RESPONSE......")
            response = ollama.chat(
                model=self.model,
                messages=messages,
                stream=False,
                think=False,
                # format="json"
            )

            print("[AI]:", response['message'])

            return response['message']['content']
            
        except Exception as e:
            raise RuntimeError(f"Ollama generation error: {e}") from e


    def stream_generate(self, messages):
        """Generate a response and yield its content chunk by chunk"""

        if not messages:
            raise ValueError("Messages can't be blank")

        try:
            print("[LLM] Starting token streaming...")

            response = ollama.chat(
                model=self.model,
                messages=messages,
                stream=True,
                think=False
            )

            for chunk in response:
                content = chunk['message']['content']
                if content:
                    yield content

            print("\n [LLM] Streaming completed")

        except Exception as e:
            raise RuntimeError(f"Ollama streaming error: {e}") from e