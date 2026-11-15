from agents.llm import Oll_LLM
from agents.registry import ToolRegistry
from agents.executor import ToolExecutor
from agents.planner import AgentPlanner
from agents.orchestrator import AgentOrchestrator
from agents.memory_manager import MemoryManager
import json
from django.contrib.auth import get_user_model

llm = Oll_LLM()
registry = ToolRegistry()
memory_manager = MemoryManager(llm=llm)

User = get_user_model()
user = User.objects.first()

# tools 
def add_numbers(a, b):
    calc = a + b
    return f"{calc}.00"

def multiply_numbers(a, b):
    return a * b

registry.register(
    name="multiply_numbers",
    description="Multiplies two numbers.",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "required": ["a", "b"],
        "additionalProperties": False
    },
    function=multiply_numbers
)

# register tools 
registry.register(
    name="add_numbers",
    description="Adds two numbers.",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "required": ["a", "b"],
        "additionalProperties": False
    },
    function=add_numbers
)


print(f"[TOOLS]: {registry.tools}")

# initialize executor 
executor = ToolExecutor(registry)
# initialize planner 
planner = AgentPlanner(llm, registry)
# initialize orchestrator 
agent = AgentOrchestrator(planner=planner, executor=executor, memory_manager=memory_manager, max_steps=5)

# user request
# cont = "Write a simple Python function that checks whether a number is even"
# cont = "What is the difference between Django and Flask?"
cont = "I'm a fullstack developer. I use Django for backend development and Svelte 5 for frontend development"
messages = [{
    "role": "user",
    "content": (cont)
}]

# run agent
result = agent.run(messages, user=user)

print("\n========== AGENT RESPONSE ============\n")
print(result)
print("\n========== EXECUTION HISTORY ============\n")

for item in result["history"]:
    print(item)

# for tool in registry.list_tools():
#     print("[REGISTERED TOOLS]:", repr(tool.name))

# print("\n ========= AVAILABLE TOOLS =========== \n")
# print(json.dumps(registry.get_schemas(), indent=4))