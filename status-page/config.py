from pydantic_settings import BaseSettings
import os, redis

class Settings(BaseSettings):
    REDIS_PORT: str = os.getenv("REDIS_PORT")
    REDIS_DB_N: str = os.getenv("REDIS_DB_N")
    SSL_CA_CERT: str = os.getenv("SSL_CA_CERT")

settings = Settings()

redis_connect = redis.Redis(
    host="redis",
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB_N,
    ssl=True,
    ssl_cert_reqs="required",
    ssl_keyfile="status-page.key",
    ssl_certfile="status-page.crt",
    ssl_ca_certs=settings.SSL_CA_CERT
)