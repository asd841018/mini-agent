import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from src.tools.example import build_tools, TOOLS

load_dotenv()

class PlanExecutor:
    def __init__(self, model: str = "gpt-4o"):
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        self.plan_model = model
        self.execute_model = model
        
        
    def plan(self, message: dict[str, str]):
        planner_prompt = """
You are a planning agent. Given a user objective, produce a concise, ordered plan to solve it.

Rules:
- Output ONLY valid JSON: {"steps": ["step 1", "step 2", ...]}
- Each step must be a single, concrete, self-contained action that an executor with tools can perform in one turn.
- Do NOT execute anything. Do NOT call tools. Do NOT add commentary.
- Keep the plan minimal: no redundant or speculative steps.
- The final step's output should directly answer the user's request.
"""     
        messages = [{
            "role": "system", "content": planner_prompt
        }]
        messages.append(message)
        response = self.client.chat.completions.create(
                model=self.plan_model,
                messages=messages,
                tools=build_tools(),
                tool_choice="none",         # ← 但禁止他呼叫
                # response_format={"type": "json_object"},
            )
        return response.choices[0].message.content
    
    def execute(self,):
        pass
        
    def run(self, prompt: str):
        message =  [
            {"role": "user", "content": prompt},
        ]
        # while True:
            # response = self.client.chat.completions.create(
            #     model=self.model,
            #     messages=messages,
            #     tools=build_tools(),
            # )
        plan_response = self.plan(message[-1])
        print(plan_response)
            # msg = response.choices[0].message
            
            # if not msg.tool_calls:
            #     print(msg.content)
            #     break
            
            # # 重要:要把 assistant 的訊息(含 tool_calls)加回 messages，才能讓模型知道 tool_calls 是對應到哪一個訊息的
            # messages.append(msg)
            
            # for call in msg.tool_calls:
            #     name = call.function.name
            #     args = json.loads(call.function.arguments)
            #     try:
            #         result = TOOLS[name].invoke(args)
            #         print(f"Tool call: {name} with args {args} returned {result}")
            #     except Exception as e:
            #         result = f"Error: {e}"
            #     # Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'
            #     messages.append({
            #         "role": "tool",
            #         "tool_call_id": call.id,
            #         "content": str(result),
            #     })
        return plan_response
    
if __name__ == "__main__":
    executor = PlanExecutor()
    prompt = "幫我算一下 (132590235 + 123523) * 2?"
    response = executor.run(prompt)