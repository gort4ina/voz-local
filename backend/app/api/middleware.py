import json

from starlette.formparsers import MultiPartException


class UploadTooLarge(MultiPartException):
    pass


class BodySizeLimitMiddleware:
    """Limit raw streamed body before Starlette spools multipart parts to disk."""

    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = 0

        async def reject():
            body = json.dumps({"detail": "O envio excede o limite de tamanho."}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": body})

        if length > self.max_bytes:
            return await reject()
        total, exceeded, started = 0, False, False

        async def limited_receive():
            nonlocal total, exceeded
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    exceeded = True
                    raise UploadTooLarge("Upload limit exceeded")
            return message

        async def guarded_send(message):
            nonlocal started
            if exceeded:
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except UploadTooLarge:
            exceeded = True
        if exceeded and not started:
            await reject()
