from app_pkg import create_app
import socket


app = create_app()


if __name__ == '__main__':
    from waitress import serve

    host = '0.0.0.0'
    port = 5000

    # Compose local and LAN URLs for convenience
    urls = [f"http://127.0.0.1:{port}"]
    try:
        # Robust way to determine LAN IP without external traffic
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
        if lan_ip and lan_ip != "127.0.0.1":
            urls.append(f"http://{lan_ip}:{port}")
    except Exception:
        pass

    app.logger.info(
        "Application started. Available at: " + ", ".join(urls)
    )

    serve(app, host=host, port=port)