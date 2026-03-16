import subprocess
import uuid

from django.conf import settings

_AUTH_ERROR_KEYWORDS = ["Token refresh failed", "refresh_token_reused", "401"]
_STDOUT_ERROR_KEYWORDS = ["Error calling Codex", "response failed"]


class LLMAuthError(RuntimeError):
    pass


def ask_llm(prompt: str, timeout_seconds: int = 25) -> str:
    nanobot_bin = settings.NANOBOT_BIN
    result = subprocess.run(
        [nanobot_bin, "agent", "--no-markdown", "-s", str(uuid.uuid4()), "-m", prompt],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        message = "LLM 실행이 비정상 종료되었습니다"
        if stderr:
            message = f"{message}: {stderr}"
        if any(kw in stderr for kw in _AUTH_ERROR_KEYWORDS):
            raise LLMAuthError(message)
        raise RuntimeError(message)

    stdout = (result.stdout or "").strip()
    if not stdout:
        raise RuntimeError("LLM 응답이 비어있습니다")

    if any(kw in stdout for kw in _STDOUT_ERROR_KEYWORDS):
        raise RuntimeError(f"LLM 응답에 에러가 포함되어 있습니다: {stdout[:200]}")

    return stdout
