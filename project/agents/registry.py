"""STORES AND MANAGES THE TOOLS AVAILABLE TO THE AGENT"""

from dataclasses import dataclass
from typing import Callable

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict 
    function: Callable

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, description: str, parameters: dict, function: Callable):
        if name in self.tools:
            raise ValueError(f"Tool '{name}' is already registered")

        if not callable(function):
            raise TypeError("Tool function must be callable.")

        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function
        )

        self.tools[name] = tool

        return tool

    def get_tool(self, name):
        return self.tools.get(name)

    def list_tools(self):
        return list(self.tools.values())

    def get_schemas(self):
        schemas = []

        for tool in self.tools.values():
            schemas.append({
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.parameters
            })

        return schemas

    def unregister(self, name):
        if name not in self.tools:
            return False

        del self.tools[name]
        return True