"""
title: Pyodide Code Execution
author: EntropyYue
author_url: https://github.com/EntropyYue/pyodide-code-execution
funding_url: https://github.com/EntropyYue/pyodide-code-execution
version: 0.0.1
"""

from collections.abc import Callable
from typing import Any


class Tools:
    def __init__(self) -> None:
        return

    async def run_python_code(
        self, python_code: str, __event_call__: Callable[[dict], Any] | None = None
    ) -> dict[str, str]:
        """
        Use Pyodide to execute the provided Python code and return the output.

        :param python_code: The Python code to execute.

        :return: The output from the executed code, when `status` is not "OK", report the `status` field first.
        """
        if not __event_call__:
            raise

        result = await __event_call__(
            {
                "type": "execute",
                "data": {
                    "code": r"""{{src/pyodide.js}}""".replace("[[code]]", python_code),
                },
            }
        )

        return result
