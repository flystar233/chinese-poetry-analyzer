import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, g


def create_app() -> Flask:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
    )

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # ----- Logging setup -----
    logs_dir = os.path.join(base_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'app.log'),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8',
    )
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    file_handler.setFormatter(formatter)

    # Attach handlers (avoid duplicates when reloading)
    if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        app.logger.addHandler(file_handler)

    # Ensure console output in addition to file
    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

    app.logger.setLevel(logging.INFO)

    # Also route third-party logs (e.g., waitress) to the same level
    logging.getLogger('waitress').setLevel(logging.INFO)

    # Immediate init log to confirm logging is working even before serving
    app.logger.info("Application initialized. Logging configured. Waiting for server to start...")

    # ----- Per-request access logging -----
    @app.before_request
    def _log_request_start():
        try:
            import time
            g._request_start_time = time.perf_counter()
        except Exception:
            g._request_start_time = None

    @app.after_request
    def _log_request_end(response):
        try:
            import time
            duration_ms = None
            if getattr(g, '_request_start_time', None) is not None:
                duration_ms = (time.perf_counter() - g._request_start_time) * 1000.0

            # Skip very noisy static requests at INFO level
            is_static = request.path.startswith('/static/')
            if duration_ms is not None:
                msg = (
                    f"{request.remote_addr} {request.method} {request.path} "
                    f"{response.status_code} {duration_ms:.1f}ms"
                )
            else:
                msg = (
                    f"{request.remote_addr} {request.method} {request.path} "
                    f"{response.status_code}"
                )

            if is_static:
                app.logger.debug(msg)
            else:
                app.logger.info(msg)
        except Exception:
            # Never fail the response due to logging
            pass
        return response

    return app


