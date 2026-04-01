from dotenv import load_dotenv
load_dotenv()

import uvicorn

from resonarr.config.settings import READ_API_HOST, READ_API_PORT
from resonarr.transport.http.fastapi_app import create_app
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("read-api-server")

    print("=== Resonarr Read API Server ===")
    print(f"[INFO] Listening on http://{READ_API_HOST}:{READ_API_PORT}")
    print("[INFO] Routes:")
    print("[INFO]   GET /healthz")
    print("[INFO]   GET /api/v1/catalog/records")
    print("[INFO]   GET /api/v1/dashboard/home")
    print("[INFO] This transport is snapshot-backed only.")
    print("[INFO] No refresh or mutation endpoints are exposed.")

    uvicorn.run(
        create_app(),
        host=READ_API_HOST,
        port=READ_API_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
