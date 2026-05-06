from __future__ import annotations

import argparse
import json
import math
import os
from pprint import pprint
from typing import Any


DEFAULT_MODEL = "openai:gpt-5.4"


def _clean_number(value: Any) -> float | None:
    """Convert pandas/numpy values into plain JSON-friendly floats."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None
    return round(number, 4)


def _latest_value(series: Any) -> float | None:
    """Return the latest non-empty numeric value from a pandas Series."""
    if series is None or series.empty:
        return None
    return _clean_number(series.dropna().iloc[-1]) if not series.dropna().empty else None


def get_stock_snapshot(symbol: str, period: str = "6mo") -> str:
    """Get recent stock price data and simple indicators for one ticker symbol.

    這是一個 Deep Agent tool。模型如果需要股票資料，就可以呼叫它。
    symbol 使用 Yahoo Finance 格式，例如：
    - AAPL: Apple
    - TSLA: Tesla
    - 2330.TW: 台積電
    - 0050.TW: 元大台灣50

    period 可以用 yfinance 支援的區間，例如 1mo、3mo、6mo、1y。
    """
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    try:
        history = ticker.history(period=period, interval="1d", auto_adjust=True)
    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "symbol": symbol,
                "period": period,
                "error": f"Failed to fetch stock data: {exc}",
            },
            ensure_ascii=False,
        )

    if history.empty:
        return json.dumps(
            {
                "ok": False,
                "symbol": symbol,
                "error": "No price data returned. Check the ticker symbol.",
            },
            ensure_ascii=False,
        )

    close = history["Close"]
    volume = history["Volume"]

    # 簡單技術指標：20 日均線、50 日均線、14 日 RSI。
    sma20 = close.rolling(window=20).mean()
    sma50 = close.rolling(window=50).mean()
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(window=14).mean()
    losses = (-delta.clip(upper=0)).rolling(window=14).mean()
    rsi14 = 100 - (100 / (1 + gains / losses))

    latest_close = _latest_value(close)
    previous_close = _clean_number(close.iloc[-2]) if len(close) >= 2 else None
    change_percent = None
    if latest_close is not None and previous_close not in (None, 0):
        change_percent = round((latest_close - previous_close) / previous_close * 100, 2)

    try:
        currency = ticker.fast_info.get("currency")
    except Exception:
        currency = None

    result = {
        "ok": True,
        "symbol": symbol,
        "period": period,
        "currency": currency,
        "latest_date": str(history.index[-1].date()),
        "latest_close": latest_close,
        "previous_close": previous_close,
        "daily_change_percent": change_percent,
        "sma20": _latest_value(sma20),
        "sma50": _latest_value(sma50),
        "rsi14": _latest_value(rsi14),
        "latest_volume": _clean_number(volume.iloc[-1]),
        "data_points": len(history),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


SYSTEM_PROMPT = """
你是一個謹慎的股票分析師 Deep Agent 範例。

請用繁體中文回答。
如果使用者要求分析股票，請先用 get_stock_snapshot 取得近期價格與技術指標。
分析請包含：
- 價格與日漲跌
- 均線狀態
- RSI 動能狀態
- 主要風險
- 簡短結論：偏多 / 中性 / 偏空

不要保證漲跌，不要直接叫使用者買賣。
最後提醒：這只是教育用途範例，不是投資建議。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A minimal LangChain Deep Agents example."
    )
    parser.add_argument(
        "message",
        nargs="?",
        default="請用 2330.TW 做一個簡短股票分析。",
        help="User message to send to the deep agent.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"LangChain model string. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print agent state updates after each graph step.",
    )
    parser.add_argument(
        "--debug-events",
        action="store_true",
        help="Print lower-level LangGraph debug events.",
    )
    parser.add_argument(
        "--subgraphs",
        action="store_true",
        help="Include subagent/subgraph events when streaming.",
    )
    return parser.parse_args()


def build_agent(model: str):
    """Create a Deep Agent.

    create_deep_agent 會建立一個 LangGraph runnable。
    除了我們傳入的 get_stock_snapshot tool，Deep Agents 還會自帶一些能力，
    例如 todo list、虛擬檔案系統、subagent task tool 等。
    """
    from deepagents import create_deep_agent

    return create_deep_agent(
        model=model,
        tools=[get_stock_snapshot],
        system_prompt=SYSTEM_PROMPT,
    )


def get_message_content(message: Any) -> str:
    """Read content from either LangChain message objects or plain dicts."""
    if hasattr(message, "content"):
        return str(message.content)
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)


def print_final_response(result: dict[str, Any]) -> None:
    """Print the last message returned by the agent."""
    messages = result.get("messages", [])
    if not messages:
        print(result)
        return

    print(get_message_content(messages[-1]))


def run_with_trace(agent: Any, message: str, *, debug_events: bool, subgraphs: bool) -> None:
    """Stream and print the agent's internal steps.

    stream_mode="updates" 適合看 agent 每一步做了什麼：
    - model node 產生 tool call
    - tool node 回傳 tool result
    - model node 產生最後回答

    stream_mode="debug" 會更吵，適合真的要追 LangGraph event。
    """
    payload = {"messages": [{"role": "user", "content": message}]}
    stream_mode = "debug" if debug_events else "updates"
    latest_result: dict[str, Any] | None = None

    for index, event in enumerate(
        agent.stream(payload, stream_mode=stream_mode, subgraphs=subgraphs),
        start=1,
    ):
        print(f"\n=== {stream_mode.upper()} EVENT {index} ===")
        pprint(event, width=120, sort_dicts=False)

        # updates mode 會分段回傳局部 state；最後一段通常包含 messages。
        if isinstance(event, dict):
            for value in event.values():
                if isinstance(value, dict) and "messages" in value:
                    latest_result = value

    if latest_result is not None:
        print("\n=== FINAL RESPONSE ===")
        print_final_response(latest_result)


def main() -> None:
    args = parse_args()

    # 讀取 .env 裡的 OPENAI_API_KEY，這樣不用每次都手動 export。
    from dotenv import load_dotenv

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("請先在環境變數或 .env 設定 OPENAI_API_KEY")

    agent = build_agent(args.model)

    if args.trace or args.debug_events:
        run_with_trace(
            agent,
            args.message,
            debug_events=args.debug_events,
            subgraphs=args.subgraphs,
        )
        return

    # Deep Agents 的輸入格式跟 LangChain/LangGraph 慣例一樣：
    # {"messages": [{"role": "user", "content": "..."}]}
    result = agent.invoke({"messages": [{"role": "user", "content": args.message}]})
    print_final_response(result)


if __name__ == "__main__":
    main()
