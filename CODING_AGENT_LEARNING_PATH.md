# Coding Agent 學習路徑

這份路線是給「想自己做一個 coding agent」的人看的，不是要你一次讀懂整個 Hermes Agent。Hermes 很大，但你真正需要先抓住的是四件事：

1. Agent loop：模型、messages、tools、tool results 之間如何循環。
2. Tool registry：tool schema 怎麼提供給模型，tool call 怎麼 dispatch 到本地函式。
3. Coding sandbox：怎麼讓 agent 安全地讀檔、改檔、跑測試。
4. MCP：怎麼把外部工具服務用同一套 tool 介面接進 agent。

## 0. 先建立一張 mental model

最小 coding agent 其實長這樣：

```text
User prompt
  -> messages
  -> LLM call with tool schemas
  -> assistant response
       -> no tool_calls: final answer
       -> has tool_calls:
            -> execute tool locally / via MCP
            -> append tool result to messages
            -> loop back to LLM
```

可以先不要管 memory、subagent、TUI、gateway、plugins、cron。那些都是工程化加值，不是第一天要懂的核心。

## 1. 在 Hermes 裡只看這幾個入口

讀 Hermes 時，建議照這個順序，不要從檔案頂部一路硬啃。

| 目標 | 先看檔案 | 看什麼 |
| --- | --- | --- |
| Agent loop | `run_agent.py` | `AIAgent.run_conversation()` |
| Tool schemas 來源 | `run_agent.py`, `model_tools.py` | `self.tools = get_tool_definitions(...)` |
| Tool dispatch | `model_tools.py` | `handle_function_call(...)` |
| Tool registry | `tools/registry.py` | `register(...)`, `dispatch(...)` |
| Toolset 控制 | `toolsets.py` | 哪些 tools 會暴露給 agent |
| MCP 能力 | `skills/mcp/`, `optional-skills/mcp/`, docs | MCP 是怎麼被包成 skill/tool 的 |

Hermes 的主 loop 大約在：

- `run_agent.py` 的 `AIAgent.run_conversation()`
- 裡面的 `# Main conversation loop`
- tool call branch 大約是 `if assistant_message.tool_calls:`
- tool 執行會進 `_execute_tool_calls(...)`
- 一般 tools 最後會走到 `model_tools.handle_function_call(...)`

你要學 agent，不需要先懂全部細節。先把這條主線畫出來就夠了。

## 2. 第一階段：做一個最小 Chat Agent

目標：先做一個沒有 tools 的 agent。

功能：

- 接收 user message。
- 建立 `messages`。
- 呼叫 LLM。
- 印出 assistant response。

你要理解：

- `system` message 放什麼。
- `user` message 放什麼。
- `assistant` response 怎麼回來。
- conversation history 為什麼是 agent 的短期記憶。

最小形狀：

```python
messages = [
    {"role": "system", "content": "You are a helpful coding assistant."},
    {"role": "user", "content": user_prompt},
]

response = client.chat.completions.create(
    model=model,
    messages=messages,
)

print(response.choices[0].message.content)
```

練習：

1. 寫一個 `mini_agent.py`。
2. 支援連續對話，讓 messages 保留歷史。
3. 加一個 `max_turns`，避免無限對話。

## 3. 第二階段：加上 tool calling

目標：讓模型可以呼叫你提供的本地函式。

先做三個 tools：

| Tool | 用途 |
| --- | --- |
| `read_file(path)` | 讀取檔案內容 |
| `list_files(path)` | 列出目錄 |
| `run_tests(command)` | 執行測試或 shell command |

核心概念：

1. Tool schema 是給模型看的「可用工具說明」。
2. Tool handler 是你本地真正執行的函式。
3. Tool result 必須塞回 messages，讓模型繼續推理。

最小 loop：

```python
while step < max_steps:
    response = call_llm(messages, tools=tool_schemas)
    msg = response.choices[0].message

    if not msg.tool_calls:
        return msg.content

    messages.append(msg)

    for tool_call in msg.tool_calls:
        result = dispatch_tool(tool_call.function.name, tool_call.function.arguments)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        })
```

練習：

1. 做一個 `ToolRegistry`。
2. `register(name, schema, handler)`。
3. `dispatch(name, args)`。
4. 所有 handler 都回傳字串或 JSON 字串。

對照 Hermes：

- `tools/registry.py` 就是比較完整的 registry。
- `model_tools.py::handle_function_call(...)` 就是 dispatch 層。
- `run_agent.py::_execute_tool_calls(...)` 就是 agent loop 裡執行 tool 的地方。

## 4. 第三階段：讓它變成 coding agent

目標：agent 能夠讀 code、修改 code、跑測試。

最小 coding agent 需要這些 tools：

| Tool | 建議限制 |
| --- | --- |
| `read_file` | 限制在 workspace 內 |
| `write_file` | 只允許 workspace 內 |
| `apply_patch` | 比整檔覆寫更安全 |
| `search` | 用 `rg` 搜尋 |
| `run_command` | 預設只允許 safe commands |

建議你一開始不要做太自由的 shell tool。Coding agent 很快就會變成「模型可以亂跑任何命令」。比較好的做法是：

- 先支援 `rg`、`pytest`、`npm test` 這種 allowlist。
- 寫檔用 patch，不要直接讓 agent 任意覆蓋。
- 所有路徑都 resolve 成 absolute path 後檢查是否在 workspace 內。
- 每次 tool call 都記錄 log。

練習：

1. 給 agent 一個小型 Python 專案。
2. 要它修一個 failing test。
3. 限制它只能用 `read_file`、`search`、`apply_patch`、`run_tests`。
4. 看它是否能完成「讀錯誤 -> 找檔案 -> 修改 -> 跑測試 -> 回報」。

## 5. 第四階段：加入狀態與壓縮

Agent loop 跑久了會遇到 context 太長的問題。

你可以先做三種狀態：

| 狀態 | 內容 |
| --- | --- |
| Transcript | 完整 messages |
| Working memory | 目前任務、已知事實、待辦 |
| Summary | 壓縮過的歷史 |

最小策略：

1. messages 超過某個長度時，把舊 messages 摘要成 summary。
2. 保留最近 N 則 messages。
3. 把 summary 放回 system 或 developer context。

練習：

1. 每 10 個 tool calls 做一次 summary。
2. summary 必須包含已修改檔案、測試結果、下一步。
3. 故意給 agent 一個長任務，觀察壓縮後有沒有忘記重點。

## 6. 第五階段：理解 MCP

MCP 可以先這樣理解：

```text
內建 tool:
  agent process 直接呼叫 Python function

MCP tool:
  agent process 透過 MCP client 呼叫外部 MCP server
```

也就是說，MCP 不是 agent loop 的替代品。MCP 是 tool layer 的一種來源。

你的 agent 可以把 tools 分成兩類：

```text
ToolRegistry
  - local tools
      - read_file
      - apply_patch
      - run_tests
  - mcp tools
      - github.search_issues
      - browser.navigate
      - database.query
```

對 agent loop 來說，它們最好長得一樣：

```python
result = registry.dispatch(tool_name, args)
```

差別只在 registry 裡：

```python
if tool_name in local_tools:
    return local_tools[tool_name](args)

if tool_name in mcp_tools:
    return mcp_client.call_tool(tool_name, args)
```

練習：

1. 先做 fake MCP：用一個 class 模擬 `list_tools()` 和 `call_tool()`。
2. 把 fake MCP tools 注入你的 `ToolRegistry`。
3. 確認 agent loop 不需要知道 tool 是 local 還是 MCP。
4. 再接真正的 MCP client。

這個抽象很重要：agent loop 應該保持單純，複雜度放在 tool adapter。

## 7. 第六階段：加入 planning

Coding agent 如果只靠一步一步 tool call，容易亂走。你可以讓它每次任務開始先產生 plan。

簡單做法：

1. 第一輪要求模型輸出 plan。
2. 把 plan 存進 working memory。
3. 每次 tool result 回來後，要求模型更新目前狀態。
4. 最後回報「做了什麼、驗證了什麼、還有什麼風險」。

你可以把 prompt 寫成：

```text
Before editing code:
1. Inspect relevant files.
2. State the smallest safe change.
3. Apply patch.
4. Run targeted verification.
5. Report changed files and test evidence.
```

練習：

1. 做 `plan.md` 輸出。
2. 每次 tool call 後更新 `todo`。
3. 如果測試失敗，要求 agent 先分析失敗原因再改。

## 8. 第七階段：子代理與並行

這一步先不要急。等你的單 agent loop 穩定後再做。

子代理適合：

- 一個 agent 搜尋 codebase。
- 一個 agent 寫測試。
- 一個 agent 做 code review。
- 主 agent 整合結果。

但第一版可以不用真的平行。先做同步版：

```text
parent agent
  -> delegate_task(goal)
       -> child agent run_conversation(...)
       -> child summary
  -> parent continues
```

對照 Hermes：

- `tools/delegate_tool.py` 是 delegation tool。
- parent 仍然是主 loop。
- child agent 本質上也是另一個 agent loop。

## 9. 建議你的 MVP 規格

先做一個叫 `tiny-coding-agent` 的小專案。

檔案結構：

```text
tiny-coding-agent/
  agent.py
  llm_client.py
  tool_registry.py
  tools/
    filesystem.py
    shell.py
    patch.py
    mcp_adapter.py
  memory.py
  prompts.py
  examples/
    broken_python_project/
```

第一版完成條件：

1. 可以對話。
2. 可以 tool call。
3. 可以讀檔、搜尋、打 patch、跑測試。
4. 可以修一個小 bug。
5. 有 max iterations。
6. 有 workspace path sandbox。
7. 有 tool call log。
8. agent loop 不知道 tool 是 local 還是 MCP。

## 10. 推薦閱讀順序

在 Hermes 裡照這樣讀：

1. `run_agent.py::AIAgent.run_conversation()`
2. `run_agent.py::_execute_tool_calls(...)`
3. `model_tools.py::handle_function_call(...)`
4. `tools/registry.py`
5. `toolsets.py`
6. `tools/` 裡挑 2 到 3 個簡單 tool 看就好
7. `tools/delegate_tool.py`
8. MCP 相關 docs 和 skills

不要一開始讀：

- gateway
- TUI
- cron
- memory provider plugins
- kanban
- dashboard
- release scripts

那些都很有趣，但會讓你在還沒學會 agent loop 前就迷路。

## 11. 你真正要學會的設計問題

做 coding agent 時，最重要的不是「怎麼 call LLM」，而是這些邊界：

| 問題 | 你要做的決策 |
| --- | --- |
| Agent 何時停止？ | final answer、max iterations、budget、interrupt |
| Tool 能做什麼？ | allowlist、sandbox、approval |
| Tool 結果怎麼回模型？ | role=tool message、JSON、錯誤格式 |
| 修改檔案怎麼安全？ | patch、diff、workspace boundary |
| 怎麼驗證成功？ | tests、lint、typecheck、smoke run |
| Context 太長怎麼辦？ | summary、working memory、recent messages |
| MCP 怎麼接？ | MCP tools normalize 成普通 tool schema |
| Agent 失敗怎麼恢復？ | logs、retry、fallback、state checkpoint |

## 12. 一個 4 週學習節奏

### Week 1：Agent loop

- 寫純聊天 agent。
- 加 messages history。
- 加 max iterations。
- 讀 Hermes 的 `run_conversation()` 主 loop。

完成標準：你可以手寫出「LLM -> tool_calls -> tool result -> LLM」流程。

### Week 2：Tools

- 寫 `ToolRegistry`。
- 做 `read_file`、`search`、`run_command`。
- 加 tool schema。
- 加 tool result messages。

完成標準：模型能自己決定讀哪個檔案。

### Week 3：Coding workflow

- 加 `apply_patch`。
- 加 workspace sandbox。
- 加 test runner。
- 做一個 failing test 修復 demo。

完成標準：agent 可以完成一個小型 bugfix。

### Week 4：MCP 與工程化

- 做 MCP adapter。
- 將 MCP tools normalize 成 registry tools。
- 加 logs、summary、basic planning。
- 寫一份自己的 architecture note。

完成標準：local tool 和 MCP tool 對 agent loop 來說是同一種東西。

## 13. 最小心法

先把 agent loop 寫小，然後只在必要時加東西。

好的 coding agent 不是因為 loop 很複雜，而是因為邊界清楚：

- 模型負責決策。
- Tool 負責副作用。
- Registry 負責連接。
- Sandbox 負責安全。
- Tests 負責驗證。
- Memory 負責不忘事。
- MCP 負責外部能力接入。

只要這幾個角色分乾淨，你的小 agent 就已經有了長成大型系統的骨架。
