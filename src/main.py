"""
title: Pyodide Code Execution
author: EntropyYue
author_url: https://github.com/EntropyYue/pyodide-code-execution
funding_url: https://github.com/EntropyYue/pyodide-code-execution
version: 0.0.2
"""

from collections.abc import Callable
from typing import Any, TypedDict
import uuid

from fastapi import Request

from open_webui.config import WEBUI_URL
from open_webui.models.users import UserModel
from open_webui.utils.files import get_image_url_from_base64
from pydantic import BaseModel, Field


class Result(TypedDict):
    stdout: str
    stderr: str
    status: str


OVERLOAD_SHOW = r"""
{{src/show.py}}
""".strip()

JS_CODE = r"""
{{src/pyodide.js}}
""".strip()


class Tools:
    class Valves(BaseModel):
        STATUS: bool = Field(default=True, description="Enable status updates.")

    def __init__(self) -> None:
        self.valves = self.Valves()

    async def run_python_code(
        self,
        python_code: str,
        __request__: Request,
        __user__: dict | None = None,
        __metadata__: dict | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
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
        emitter = EventEmitter(self.valves, __event_emitter__)
        execution_tracker = CodeExecutionTracker(
            name="Python Code Execution", code=python_code, language="python"
        )

        await emitter.code_execution(execution_tracker)

        result: Result = await __event_call__(
            {
                "type": "execute",
                "data": {
                    "code": JS_CODE.replace("[[code]]", python_code).replace(
                        """[[matplotlib_overload]]""", OVERLOAD_SHOW
                    ),
                },
            }
        )

        stdout_lines = result.get("stdout").splitlines(keepends=True)

        for i, line in enumerate(stdout_lines):
            if line.startswith("data:image/png;base64,"):
                if image_url := get_image_url_from_base64(
                    request=__request__,
                    base64_image_string=line,
                    metadata=__metadata__,
                    user=UserModel(**__user__) if __user__ else None,
                ):
                    image_url = f"{WEBUI_URL}{image_url}"
                    stdout_lines[i] = f"![Output Image]({image_url})"
                    execution_tracker.add_file("Output Image", image_url)

        stdout = "".join(stdout_lines)

        if result.get("status") == "OK":
            execution_tracker.set_output(stdout or "None")
        if result.get("status") != "OK":
            execution_tracker.set_error(result.get("status", result.get("stderr")))

        await emitter.code_execution(execution_tracker)

        return {
            "stdout": stdout,
            "stderr": result.get("stderr"),
            "status": result.get("status"),
        }


class EventEmitter:
    """
    Helper wrapper for OpenWebUI event emissions.
    """

    def __init__(
        self,
        valves: Tools.Valves,
        event_emitter: Callable[[dict], Any] | None = None,
    ):
        self.event_emitter = event_emitter
        self.valves = valves

    async def _emit(self, typ, data, twice):
        if not self.event_emitter:
            return None
        result = await self.event_emitter(
            {
                "type": typ,
                "data": data,
            }
        )
        return result

    async def code_execution(self, code_execution_tracker):
        await self._emit(
            "citation", code_execution_tracker._citation_data(), twice=True
        )


class CodeExecutionTracker:
    def __init__(self, name, code, language):
        self._uuid = str(uuid.uuid4())
        self.name = name
        self.code = code
        self.language = language
        self._result = {}

    def set_error(self, error):
        self._result["error"] = error

    def set_output(self, output):
        self._result["output"] = output

    def add_file(self, name, url):
        if "files" not in self._result:
            self._result["files"] = []
        self._result["files"].append(
            {
                "name": name,
                "url": url,
            }
        )

    def _citation_data(self):
        data = {
            "type": "code_execution",
            "id": self._uuid,
            "name": self.name,
            "code": self.code,
            "language": self.language,
        }
        if "output" in self._result or "error" in self._result:
            data["result"] = self._result
        return data
