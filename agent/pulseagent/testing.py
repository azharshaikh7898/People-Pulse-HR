"""A scripted chat model for deterministic tests and offline eval runs (no API key, no cost)."""
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


def tool_call(name: str, args: dict, call_id: str) -> dict:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


class ScriptedChatModel(BaseChatModel):
    """Returns pre-written AI messages in order. Records what it was shown."""
    script: list[AIMessage]
    seen: list[list[BaseMessage]] = []
    _cursor: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any):
        return self  # tool schemas are irrelevant to a scripted model

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.seen.append(list(messages))
        idx = min(self._cursor, len(self.script) - 1)  # repeat the last message if the script runs out
        self._cursor += 1
        message = self.script[idx].model_copy(update={"id": None})  # fresh id each time: LangGraph dedupes by id
        return ChatResult(generations=[ChatGeneration(message=message)])
