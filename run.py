import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # host="0.0.0.0" cho phép các máy khác trong cùng mạng Wi-Fi/LAN truy cập
    app.run(host="0.0.0.0", port=port, debug=True)
