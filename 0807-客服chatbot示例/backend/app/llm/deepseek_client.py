"""DeepSeek 调用封装：OpenAI 兼容 SDK，配置全部来自环境变量。"""
from __future__ import annotations

from openai import APIError, OpenAI

from app.config import get_settings
from app.logger import get_logger
from app.models import ChatMessage, MessageRole

logger = get_logger(__name__)


class DeepSeekConfigError(RuntimeError):
    """DeepSeek 未正确配置（缺少 API key 等），调用前置校验失败。"""


class DeepSeekCallError(RuntimeError):
    """DeepSeek API 调用过程中发生错误（网络、鉴权、限流等）。"""


SYSTEM_PROMPT = (
    "你是公司内部的客服助手，负责基于下面提供的知识库片段回答员工的问题。"
    "请只依据知识库内容作答；如果知识库片段不足以回答问题，明确告知用户"
    "并建议联系相关部门，不要编造流程或政策细节。回答使用简体中文，简洁明确。"
)


def build_context_prompt(knowledge_snippets: list[str]) -> str:
    if not knowledge_snippets:
        return "（未检索到相关知识库内容）"
    joined = "\n\n---\n\n".join(knowledge_snippets)
    return f"以下是检索到的相关知识库片段：\n\n{joined}"


class DeepSeekClient:
    """封装 DeepSeek Chat Completion 调用，使用 OpenAI 兼容 SDK。"""

    def __init__(self) -> None:
        self._settings = get_settings()

    def _require_client(self) -> OpenAI:
        if not self._settings.deepseek_configured:
            raise DeepSeekConfigError(
                "DeepSeek 未配置：请在 backend/.env 中设置 DEEPSEEK_API_KEY"
                "（可参考 .env.example）。"
            )
        return OpenAI(
            api_key=self._settings.deepseek_api_key,
            base_url=self._settings.deepseek_base_url,
        )

    def chat(
        self,
        history: list[ChatMessage],
        user_message: str,
        knowledge_snippets: list[str],
    ) -> str:
        """基于历史对话 + 检索到的知识片段，调用 DeepSeek 生成回复。"""
        client = self._require_client()

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": build_context_prompt(knowledge_snippets)},
        ]
        for turn in history:
            messages.append({"role": turn.role.value, "content": turn.content})
        messages.append({"role": MessageRole.user.value, "content": user_message})

        try:
            completion = client.chat.completions.create(
                model=self._settings.deepseek_model,
                messages=messages,  # type: ignore[arg-type]
            )
        except APIError as exc:
            logger.error("DeepSeek API 调用失败: %s", exc)
            raise DeepSeekCallError(f"DeepSeek API 调用失败: {exc}") from exc

        reply = completion.choices[0].message.content
        if not reply:
            raise DeepSeekCallError("DeepSeek 返回了空响应内容。")
        return reply
