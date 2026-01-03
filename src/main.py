"""
title: Pyodide Code Execution
author: EntropyYue
author_url: https://github.com/EntropyYue/pyodide-code-execution
funding_url: https://github.com/EntropyYue/pyodide-code-execution
version: 0.0.1
"""

from collections.abc import Callable
from typing import Any, TypedDict

from fastapi import Request

from open_webui.config import WEBUI_URL
from open_webui.models.users import UserModel
from open_webui.utils.files import get_image_url_from_base64


class ExecutionResult(TypedDict):
    stdout: str
    stderr: str
    status: str


OVERLOAD_SHOW = r"""
import base64
import os
from io import BytesIO

# before importing matplotlib
# to avoid the wasm backend (which needs js.document', not available in worker)
os.environ["MPLBACKEND"] = "AGG"

import matplotlib.pyplot

_old_show = matplotlib.pyplot.show
assert _old_show, "matplotlib.pyplot.show"

def show(*, block=None):
	buf = BytesIO()
	matplotlib.pyplot.savefig(buf, format="png")
	buf.seek(0)
	# encode to a base64 str
	img_str = base64.b64encode(buf.read()).decode('utf-8')
	matplotlib.pyplot.clf()
	buf.close()
	print(f"data:image/png;base64,{img_str}")

matplotlib.pyplot.show = show
""".strip()

JS_CODE = r"""
{{src/pyodide.js}}
""".strip()


class Tools:
    def __init__(self) -> None:
        return

    async def run_python_code(
        self,
        python_code: str,
        __request__: Request,
        __user__: dict | None = None,
        __metadata__: dict | None = None,
        __event_call__: Callable[[dict], Any] | None = None,
    ) -> dict[str, str]:
        """
        Use Pyodide to execute the provided Python code and return the output.
        When using Matplotlib, use the show() function.

        :param python_code: The Python code to execute.

        :return: The output from the executed code, when `status` is not "OK", report the `status` field first.
        """
        if not __event_call__:
            raise

        execution_result: ExecutionResult = await __event_call__(
            {
                "type": "execute",
                "data": {
                    "code": JS_CODE.replace("[[code]]", python_code).replace(
                        """[[matplotlib_overload]]""", OVERLOAD_SHOW
                    ),
                },
            }
        )

        stdout_lines = execution_result["stdout"].splitlines(keepends=True)

        for i, line in enumerate(stdout_lines):
            if line.startswith("data:image/png;base64,"):
                if image_url := get_image_url_from_base64(
                    request=__request__,
                    base64_image_string=line,
                    metadata=__metadata__,
                    user=UserModel(**__user__) if __user__ else None,
                ):
                    stdout_lines[i] = f"![Output Image]({WEBUI_URL}{image_url})"

        return {
            "stdout": "".join(stdout_lines),
            "stderr": execution_result["stderr"],
            "status": execution_result["status"],
        }
