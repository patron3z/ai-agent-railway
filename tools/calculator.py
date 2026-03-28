import logging
import subprocess
import sys
import tempfile
import os

logger = logging.getLogger("agent.tools.calculator")

CALCULATOR_TOOL_DEF = {
    "name": "run_python",
    "description": (
        "Execute Python code and return the output. "
        "Use for math calculations, data analysis, string processing, "
        "sorting, converting units, generating data, etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Valid Python 3 code to execute. Use print() to output results.",
            },
            "timeout": {
                "type": "integer",
                "description": "Max seconds to run (default 15, max 30)",
                "default": 15,
            },
        },
        "required": ["code"],
    },
}

# Blocked imports for security
BLOCKED_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "import shutil",
    "__import__",
    "open(",
    "exec(",
    "eval(",
    "compile(",
    "globals(",
    "locals(",
    "__builtins__",
]


def run_python(code: str, timeout: int = 15) -> str:
    """Execute Python code safely in a subprocess."""
    timeout = min(timeout, 30)

    # Basic security check
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            logger.warning(f"[run_python] blocked pattern '{pattern}' in code")
            return f"Security error: '{pattern}' is not allowed in code execution."

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout.strip()
        errors = result.stderr.strip()

        if result.returncode != 0:
            logger.warning(f"[run_python] exit code {result.returncode}")
            return f"Error (exit {result.returncode}):\n{errors}" if errors else "Execution failed with no output."

        logger.info(f"[run_python] success, {len(output)} chars output")

        if output and errors:
            return f"{output}\n\n[stderr]: {errors}"
        return output or "(no output)"

    except subprocess.TimeoutExpired:
        logger.warning(f"[run_python] timeout after {timeout}s")
        return f"Timeout: code took longer than {timeout} seconds."
    except Exception as e:
        logger.error(f"[run_python] error: {e}")
        return f"Execution error: {e}"
    finally:
        os.unlink(temp_path)
