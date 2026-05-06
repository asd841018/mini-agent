# OpenAI Text Chat Tool Loop

一個用 `uv` 管理套件、用 OpenAI 文字聊天模型跑 XML tool call 的最小 Python 範例。

## 安裝與執行

```bash
uv sync
export OPENAI_API_KEY="你的 API key"
uv run python gemma4_mlx.py "讀 README.md 並用繁體中文摘要"
```

預設模型是 `gpt-4.1`。程式會要求模型在需要工具時輸出：

```xml
<tool_use>
{"name": "read_file", "arguments": {"path": "README.md"}}
</tool_use>
```

## 常用參數

```bash
uv run python gemma4_mlx.py \
  "列出目前資料夾有哪些檔案" \
  --max-tokens 512 \
  --temperature 0.2
```

也可以換 OpenAI model ID：

```bash
uv run python gemma4_mlx.py \
  --model gpt-4.1 \
  "hello"
```
