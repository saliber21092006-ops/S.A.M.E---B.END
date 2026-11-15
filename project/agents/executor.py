"""EXECUTES TOOLS: Receives instruction from the model, find the appropraite tool, execute it and return the result

TOOL REQUEST -> RECEIVE TOOL NAME -> CHECK TOOL REGISTRY -> VALIDATE ARGUMENTS -> EXECUTE PYTHON FUNCTION -> CAPTURE RESULT -> RETURN RESULT
"""

from dataclasses import dataclass
from typing import Any

@dataclass
class ExecutionResult:
    success: bool
    tool: str
    output: Any = None
    error: str = None

class ToolExecutor:
    def __init__(self, registry):
        self.registry = registry

    def validate_arguments(self, tool, arguments):
        schema = tool.parameters
        if not isinstance(arguments, dict):
            raise ValueError('Tool arguments must be an object')

        if schema.get('type') != "object":
            return

        properties = schema.get('properties', {})
        required = schema.get('required', [])

        for field in required:
            # check requred arguments 
            if field not in arguments:
                raise ValueError(f"Missing required arguments: {field}")

        # check unexpected arguments 
        if schema.get('additionalProperties') is False:
            unexpected = set(arguments) - set(properties)
            if unexpected:
                raise ValueError(f"Unexpected arguments: {unexpected}")
            
        type_map = {
                    'string': str,
                    'integer': int,
                    'number': (int, float),
                    'boolean': bool,
                    'object': dict,
                    'array': list
                }
        
        # validate the arguments type 
        for field, value in arguments.items():
            if field not in properties:
                continue
            expected = properties[field].get('type')

            if expected not in type_map:
                continue
            actual_type = type_map[expected]

            if expected == 'integer' and isinstance(value, bool):
                raise ValueError(f"Argument '{field}' must be an interger")

            if expected == 'number' and isinstance(value, bool):
                raise ValueError(f"Argument '{field}' must be a number")

            if not isinstance(value, actual_type):
                raise ValueError(f"Argument '{field}' must be of type {expected}")

    def execute(self, tool_name, arguments):
        # step 1: retrieve tool 
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            return ExecutionResult(
                success=False,
                tool=tool_name,
                error=f"Tool '{tool_name}' does not exist"
            )

        try:
            # step 2: validate arguments 
            self.validate_arguments(tool, arguments)

            # step 3: Execute function 
            output = tool.function(**arguments)

            # step 4: return the result 
            return ExecutionResult(
                success=True,
                tool=tool_name,
                output=output
            )
        except Exception as err:
            return ExecutionResult(
                success=False,
                tool=tool_name,
                error=str(err)
            )