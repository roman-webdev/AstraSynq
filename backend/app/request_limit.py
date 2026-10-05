"""Bound upload bodies before multipart parsing, including chunked requests."""
from starlette.responses import JSONResponse

class UploadBodyLimit:
    def __init__(self, app, limit=6 * 1024 * 1024):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'] != '/api/v1/imports':
            return await self.app(scope, receive, send)
        response = JSONResponse({'detail': {'code': 'file_limit'}}, status_code=413)
        headers = dict(scope.get('headers', []))
        try:
            if int(headers.get(b'content-length', b'0')) > self.limit:
                return await response(scope, receive, send)
        except ValueError:
            return await JSONResponse({'detail': {'code': 'invalid_input'}}, status_code=400)(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > self.limit:
                return await response(scope, receive, send)
            if not message.get('more_body', False):
                break
        delivered = False
        async def replay():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
        await self.app(scope, replay, send)
