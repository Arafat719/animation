"""Opt-in mock inventory gate before submission; preflight is never cached."""

from threading import Event

from animation_studio.providers.comfy_http import ComfyHTTPExecutor


class CheckedComfyExecutor:
    is_mock = True

    def __init__(self, executor: ComfyHTTPExecutor):
        if type(executor) is not ComfyHTTPExecutor:
            raise TypeError('Expected mock Comfy HTTP executor')
        self.executor = executor

    def execute(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes:
        self.executor.preflight(graph, cancel=cancel)
        return self.executor.execute(graph, cancel=cancel)
