import os
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool

class WeatherInput(BaseModel):
    location: str = Field(..., description="The location to get the weather for")
    
class MathOperationInput(BaseModel):
    a: int = Field(..., description="The first number to operate on")
    b: int = Field(..., description="The second number to operate on")
    
class FileOperationInput(BaseModel):
    file_path: str = Field(..., description="The path of the file to read")
    
class DirectoryOperationInput(BaseModel):
    directory: str = Field(..., description="The directory to list files from")

@tool("get_weather", args_schema=WeatherInput)
def get_weather(location: str) -> str:
    # 給tool的描述必須要有，否則會被OpenAI拒絕，因為他們需要知道這個tool是幹嘛的
    """Get the current weather for a location."""
    return f"{location} is sunny with a high of 25°C."

@tool("add", args_schema=MathOperationInput)
def add(a: int, b: int) -> int:
    """Add two integers together. Use this for ANY addition, 
    even simple ones. Do not compute addition mentally."""
    return a + b

@tool("multiply", args_schema=MathOperationInput)
def multiply(a: int, b: int) -> int:
    """Multiply two integers. Use this for ANY multiplication, 
    even simple ones. Do not compute multiplication mentally."""
    return a * b

@tool("read_file", args_schema=FileOperationInput)
def read_file(file_path: str) -> str:
    """Read the contents of a file."""
    with open(file_path, "r") as file:
        return file.read()
    
@tool("list_files", args_schema=DirectoryOperationInput)
def list_files(directory: str) -> str:
    """List the files in a directory."""
    return "\n".join(os.listdir(directory))

def build_tools():
    # for openai model can see what tools are available, we need to convert the langchain tool to openai tool
    return [convert_to_openai_tool(get_weather), 
            convert_to_openai_tool(add),
            convert_to_openai_tool(multiply),
            convert_to_openai_tool(read_file),
            convert_to_openai_tool(list_files)]

# 1. 用 tool.name 當 key 建 registry
TOOLS = {t.name: t for t in [get_weather, add, multiply, read_file, list_files]}