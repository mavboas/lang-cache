from typing import Any, NamedTuple

from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app import config
from app.bank_tools import build_bank_tools

SYSTEM_PROMPT = """You are a customer support assistant for Aurora Bank.

You can only see and act on the account of the customer you are currently
talking to -- use the tools to look up their balance, recent transactions,
and card status, or to block a card. Never invent numbers or transactions;
if a tool returns "no account found", say so plainly.

Keep answers short and to the point, like a real support chat reply."""


class TokenUsageCallback(BaseCallbackHandler):
    """Sums token usage across every LLM call the agent makes during a run
    (an agent may call the model more than once: once per tool call, plus
    the final answer), so callers get one aggregate figure per request."""

    def __init__(self):
        self.prompt_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        for generation_list in response.generations:
            for generation in generation_list:
                message = getattr(generation, "message", None)
                usage = getattr(message, "usage_metadata", None) if message else None
                if not usage:
                    continue
                self.prompt_tokens += usage.get("input_tokens", 0) or 0
                self.output_tokens += usage.get("output_tokens", 0) or 0
                self.total_tokens += usage.get("total_tokens", 0) or 0


def _build_llm() -> BaseChatModel:
    if config.MODEL_PROVIDER == "TECENT":
        return ChatOpenAI(
            model=config.TECENT_MODEL,
            api_key=config.OPENAI_TECENT_KEY,
            base_url=config.TECENT_BASE_URL,
            temperature=0,
            extra_body={"reasoning": {"enabled": True}},
        )
    return ChatGoogleGenerativeAI(
        model=config.MODELO_GEMINI,
        google_api_key=config.GEMINI_API_KEY,
        temperature=0,
    )


def build_bank_agent_executor(account_id: str) -> Runnable:
    llm = _build_llm()
    tools = build_bank_tools(account_id)
    return create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)


def _extract_text(content: Any) -> str:
    """Gemini can return content as a plain string or as a list of content
    blocks (text/thought-signature/...); we only want the text parts."""
    if isinstance(content, str):
        return content
    parts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"]
    return "".join(parts)


class AgentRunResult(NamedTuple):
    response: str
    # True if the agent called any account tool (get_balance, block_card, ...)
    # to answer -- i.e. the answer depends on this customer's own data and
    # must not be reused for a different account_id.
    used_account_data: bool


def run_bank_agent(agent: Runnable, user_prompt: str, callback: "TokenUsageCallback") -> AgentRunResult:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_prompt}]},
        config={"callbacks": [callback]},
    )
    messages = result["messages"]
    used_account_data = any(isinstance(message, ToolMessage) for message in messages)
    return AgentRunResult(response=_extract_text(messages[-1].content), used_account_data=used_account_data)
