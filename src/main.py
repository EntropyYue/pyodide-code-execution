"""
title: Pyodide Code Execution
author: EntropyYue
author_url: https://github.com/EntropyYue
funding_url: https://github.com/EntropyYue/pyodide-code-execution
version: 0.1.1
"""

import uuid
from collections.abc import Callable
from typing import Any, TypedDict

from fastapi import Request
from open_webui.config import WEBUI_URL
from open_webui.models.users import UserModel
from open_webui.utils.files import get_image_url_from_base64
from pydantic import BaseModel, Field


class Result(TypedDict):
    stdout: str | None
    stderr: str | None
    result: str | None


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
    ) -> dict[str, str | None]:
        """
        Use Pyodide to execute the provided Python code and return the output.
        When using Matplotlib, use the show() function.

        :param python_code: The Python code to execute.

        :return: The output from the executed code, when `status` is not "OK", report the `status` field first.
        """
        if not __event_call__:
            return {
                "error": "Event call not available. WebSocket connection required for pyodide execution."
            }

        emitter = EventEmitter(self.valves, __event_emitter__)
        execution_tracker = CodeExecutionTracker(
            name="Python Code Execution", code=python_code, language="python"
        )

        await emitter.code_execution(execution_tracker)

        result: Result = await __event_call__(
            {
                "type": "execute:python",
                "data": {
                    "id": str(uuid.uuid4()),
                    "code": python_code,
                    "session_id": __metadata__.get("session_id")
                    if __metadata__
                    else None,
                },
            }
        )

        if stdout := result.get("stdout"):
            stdout_lines = stdout.split("\n")

            for i, line in enumerate(stdout_lines):
                if line.startswith("data:image/png;base64,") and (
                    image_url := get_image_url_from_base64(
                        request=__request__,
                        base64_image_string=line,
                        metadata=__metadata__,
                        user=UserModel(**__user__) if __user__ else None,
                    )
                ):
                    image_url = f"{WEBUI_URL}{image_url}"
                    stdout_lines[i] = f"![Output Image]({image_url})"
                    execution_tracker.add_file("Output Image", image_url)

            result["stdout"] = "\n".join(stdout_lines)

        execution_tracker.result = result

        await emitter.code_execution(execution_tracker)

        return {
            "stdout": result.get("stdout"),
            "stderr": result.get("stderr"),
            "result": result.get("result"),
        }


class TrackerResult(TypedDict, total=False):
    error: str
    output: str
    files: list[dict[str, str]]


class CodeExecutionTracker:
    def __init__(self, name: str, code: str, language: str) -> None:
        self._uuid = str(uuid.uuid4())
        self.name = name
        self.code = code
        self.language = language
        self._result: TrackerResult = {}

    @property
    def result(self) -> TrackerResult:
        return self._result

    @result.setter
    def result(self, exec_result: Result) -> None:
        self._result["output"] = (
            exec_result.get("stdout") or exec_result.get("result") or "None"
        )
        if exec_result.get("stderr"):
            self._result["output"] = ""
            self._result["error"] = exec_result["stderr"] or "Error"

    def add_file(self, name: str, url: str):
        if "files" not in self._result:
            self._result["files"] = []
        self._result["files"].append(
            {
                "name": name,
                "url": url,
            }
        )

    def citation_data(self):
        data: dict[str, str | TrackerResult] = {
            "type": "code_execution",
            "id": self._uuid,
            "name": self.name,
            "code": self.code,
            "language": self.language,
        }
        if "output" in self.result or "error" in self.result:
            data["result"] = self.result
        return data


class EventEmitter:
    def __init__(
        self,
        valves: Tools.Valves,
        event_emitter: Callable[[dict], Any] | None = None,
    ) -> None:
        self.event_emitter = event_emitter
        self.valves = valves

    async def _emit(self, typ: str, data: dict[str, Any]) -> Any:
        if not self.event_emitter:
            return None
        result = await self.event_emitter(
            {
                "type": typ,
                "data": data,
            }
        )
        return result

    async def code_execution(
        self, code_execution_tracker: CodeExecutionTracker
    ) -> None:
        await self._emit("citation", code_execution_tracker.citation_data())
