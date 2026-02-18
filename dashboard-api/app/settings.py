import os

class Settings:
    DB_HOST = os.getenv("DB_HOST","mariadb")
    DB_PORT = int(os.getenv("DB_PORT","3306"))
    DB_NAME = os.getenv("DB_NAME","upbit")
    DB_USER = os.getenv("DB_USER","upbit")
    DB_PASS = os.getenv("DB_PASS","upbitpass")
    TZ = os.getenv("TZ","Asia/Seoul")

    DOCKER_HOST = os.getenv("DOCKER_HOST","unix:///var/run/docker.sock")
    TRADER_IMAGE = os.getenv("TRADER_IMAGE","upbit-trader:latest")
    TRADER_NETWORK = os.getenv("TRADER_NETWORK","upbitnet")

    KEY_ENC_SECRET = os.getenv("KEY_ENC_SECRET","dev-only-secret-change-me")

SETTINGS = Settings()
