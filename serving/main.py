"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title='cryptoterminal', version='0.1.0')

    @app.get('/api/v1/health')
    def health() -> dict[str, str]:
        return {'status': 'ok'}

    @app.get('/')
    def root() -> dict[str, str]:
        return {'service': 'cryptoterminal', 'status': 'running'}

    return app


app = create_app()
