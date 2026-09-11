"""Authentication outside the unchanged native Cairn ASGI application."""
import hmac
import os
from pathlib import Path
from cairn.server.app import app as native_app

class AuthenticatedCairn:
    def __init__(self, app):
        self.app = app
        directory = Path(os.environ.get('WUJI_CORE_CREDENTIALS', '/run/wuji/credentials'))
        self.expected = ('Bearer ' + (directory / 'cairn_token').read_text().strip()).encode()
    async def __call__(self, scope, receive, send):
        if scope['type'] in ('http', 'websocket'):
            authorization = dict(scope.get('headers', [])).get(b'authorization', b'')
            if not hmac.compare_digest(authorization, self.expected):
                if scope['type'] == 'websocket':
                    await send({'type': 'websocket.close', 'code': 4401})
                else:
                    await send({'type':'http.response.start','status':401,'headers':[(b'content-type',b'application/json')]})
                    await send({'type':'http.response.body','body':b'{"error":"unauthorized"}'})
                return
        await self.app(scope, receive, send)

app = AuthenticatedCairn(native_app)
