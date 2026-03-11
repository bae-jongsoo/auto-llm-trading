import subprocess

from django.conf import settings


def ask_llm(prompt: str, timeout_seconds: int = 25) -> str:
    nanobot_bin = settings.NANOBOT_BIN
    result = subprocess.run(
        [nanobot_bin, "agent", "--no-markdown", "-m", prompt],
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
        raise RuntimeError(message)

    return result.stdout
