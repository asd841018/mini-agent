from __future__ import annotations

import os
from dotenv import load_dotenv
import argparse
import json

from openai import OpenAI

from tools.bash import bash
from tools.read_file import read_file
from tools.tool_parse import parse_tool_use
from tools.write_file import write_file

# load environment variables from .env file, including OPENAI_API_KEY
load_dotenv()

DEFAULT_MODEL = "gpt-5.4"
TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "bash": bash,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a simple OpenAI text chat loop with XML tool calls."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="用繁體中文簡短介紹你自己。",
        help="Text prompt to send to the model.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model id. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum number of tokens to generate.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature. Use 0 for deterministic output.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print OpenAI response metadata.",
    )
    return parser.parse_args()


def system_prompt() -> str:
    return """
You are a helpful AI coding assistant equipped with external tools.

Work autonomously. If the user's request can be completed by reading files, writing files, or running a safe local command, do it with the available tools instead of asking for permission or offering to do it later.

Do not say "I can update the file for you" when a write_file tool call can update the file. Call write_file directly.
Do not ask whether to proceed for ordinary local file edits or safe local commands.
Ask a question only when the request is ambiguous enough that choosing would likely produce the wrong file or destructive result.

[Available Tools]

1. Tool Name: read_file
   Description: Read a UTF-8 text file from the current workspace.
   Parameters:
   - path (string, required): File path relative to the workspace.
   - start_line (integer, optional): 1-based starting line. Default is 1.
   - max_lines (integer, optional): Maximum lines to read. Default is 200.

2. Tool Name: write_file
   Description: Write UTF-8 text to a file in the current workspace.
   Parameters:
   - path (string, required): File path relative to the workspace.
   - content (string, required): Text content to write.
   - append (boolean, optional): Append instead of overwrite. Default is false.
   - create_dirs (boolean, optional): Create parent directories. Default is true.

3. Tool Name: bash
   Description: Run a non-destructive bash command in the current workspace.
   Parameters:
   - command (string, required): Bash command to run.
   - cwd (string, optional): Working directory relative to the workspace.
   - timeout_seconds (integer, optional): Timeout from 1 to 300 seconds. Default is 30.
   
You must call the tools using the following format:
<tool_use>
{"name": "tool_name", "arguments": {"key": "value"}}
</tool_use>

DO NOT use ```json code block.
DO NOT include any explanations or text outside of the <tool_use> tags when calling a tool. Only include the JSON with the tool name and arguments.

After a tool result is provided, continue the original task. If more tools are needed, call another tool. If the task is complete, give a concise final answer describing what was done.
"""


def run_tool(tool_use: dict) -> dict:
    tool_name = tool_use["name"]
    arguments = tool_use["arguments"]

    if tool_name not in TOOLS:
        return {
            "ok": False,
            "error": f"unknown tool: {tool_name}",
            "available_tools": sorted(TOOLS),
        }

    try:
        return TOOLS[tool_name](**arguments)
    except Exception as exc:
        return {
            "ok": False,
            "tool": tool_name,
            "error": str(exc),
        }
        
def render_messages(messages):
    parts = []

    for message in messages:
        role = message["role"].upper()
        parts.append(f"{role}:\n{message['content']}")

    return "\n\n".join(parts)


def call_model(client: OpenAI, args: argparse.Namespace, messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": render_messages(messages)},
        ],
        max_completion_tokens=args.max_tokens,
        temperature=args.temperature,
    )

    if args.verbose:
        print("\n=== OpenAI Metadata ===")
        print(response.model_dump_json(indent=2))

    return response.choices[0].message.content or ""


def main() -> None:
    args = parse_args()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print(f"Using OpenAI model: {args.model}")

    messages = [
        {"role": "user", "content": args.prompt},
    ]
    while True:
        output_text = call_model(client, args, messages)
        print(output_text)
        tool_use = parse_tool_use(output_text)
        if not tool_use:
            print(output_text)
            break
        messages.append({"role": "assistant", "content": output_text})
        result = run_tool(tool_use)
        messages.append({
            "role": "tool",
            "content": (
                json.dumps(result, ensure_ascii=False)
                + "\n\nContinue the user's original request. If more tools are needed, call another tool. If the task is complete, give the final answer."
            ),
        })


if __name__ == "__main__":
    main()
