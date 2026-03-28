import json
import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from tools import TOOLS, TOOL_HANDLERS

logger = logging.getLogger("agent")

def _load_system_prompt() -> str:
    """Load SKILL.md as system prompt if it exists, otherwise use default."""
    skill_path = Path(__file__).parent / "SKILL.md"
    if skill_path.exists():
        content = skill_path.read_text(encoding="utf-8")
        logger.info(f"[agent] Loaded system prompt from SKILL.md ({len(content)} chars)")
        return content
    logger.warning("[agent] SKILL.md not found, using default system prompt")
    return _DEFAULT_SYSTEM_PROMPT

_DEFAULT_SYSTEM_PROMPT = """You are a helpful, intelligent AI assistant with access to the web and computation tools.

You have these skills:
- **search_web**: Search the web for current information, news, facts
- **scrape_url**: Read the full content of a webpage
- **run_python**: Execute Python code for calculations, data processing, analysis

Guidelines:
- Think step by step before acting
- Use search_web when you need current or factual information
- Use scrape_url to read full content of relevant pages from search results
- Use run_python for any math, data processing, or computation
- Always cite your sources when using web search
- Be concise but thorough
- If you're unsure, say so and search for more information
"""


SYSTEM_PROMPT = _load_system_prompt()


class Agent:
    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _call_api(self, messages: list[dict]) -> anthropic.types.Message:
        return self.client.messages.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

    def run(self, user_message: str) -> str:
        """Run the agent and return the final response."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        iterations = 0

        while iterations < config.MAX_ITERATIONS:
            iterations += 1
            logger.info(f"[agent] iteration {iterations}")

            response = self._call_api(messages)

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return "(no response)"

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = self._handle_tools(response.content)
                messages.append({"role": "user", "content": tool_results})
            else:
                logger.warning(f"[agent] unexpected stop_reason: {response.stop_reason}")
                break

        return "Max iterations reached. Please try a more specific question."

    def stream(self, user_message: str) -> Generator[str, None, None]:
        """Stream the agent response token by token, yielding text chunks."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        iterations = 0

        while iterations < config.MAX_ITERATIONS:
            iterations += 1

            # Non-streaming call when tools might be needed
            response = self._call_api(messages)

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        # Stream the final text word by word
                        words = block.text.split(" ")
                        for i, word in enumerate(words):
                            yield word + (" " if i < len(words) - 1 else "")
                return

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                # Yield tool usage info to client
                for block in response.content:
                    if block.type == "tool_use":
                        yield f"\n\n⚙️ *Using tool: **{block.name}**...*\n\n"

                tool_results = self._handle_tools(response.content)
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        yield "\n\n*(Max iterations reached)*"

    def _handle_tools(self, content: list) -> list[dict]:
        results = []
        for block in content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            logger.info(f"[tool] {tool_name}({json.dumps(tool_input)[:200]})")

            handler = TOOL_HANDLERS.get(tool_name)
            if not handler:
                result = f"Unknown tool: {tool_name}"
                is_error = True
            else:
                try:
                    result = handler(**tool_input)
                    is_error = False
                except Exception as e:
                    logger.error(f"[tool] {tool_name} error: {e}")
                    result = f"Tool error: {e}"
                    is_error = True

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
                **({"is_error": True} if is_error else {}),
            })

        return results
