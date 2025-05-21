from pydantic_settings import BaseSettings
import os
import redis
import psycopg2
import docker
import re

class Settings(BaseSettings):
    NGINX_CONTAINER: str = os.getenv("CONTAINERNAME")
    DB_CONTAINER: str = os.getenv("DB_CONTAINER")
    REDIS_PORT: str = os.getenv("REDIS_PORT")
    REDIS_DB_N: str = os.getenv("REDIS_DB_N")
    SSL_CA_CERT: str = os.getenv("SSL_CA_CERT")
    WEB_NAME: str = os.getenv("WEB_NAME")
    WEB_PORT: str = os.getenv("WEB_PORT")

settings = Settings()

# One line from nginx log for example
# 10.10.10.10 - - [12/May/2025:12:18:47 +0000] "GET /api/v1/im/incidents/318308/view?_dc=1747052336284 HTTP/1.1" 200 83 "https://10.0.0.1/" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 YaBrowser/24.7.0.0 Safari/537.36"
LOG_PARSER_REGEX=r'(::ffff:|)(?P<ip>\d+\.\d+\.\d+\.\d+)\s-\s-\s\[(?P<time>[^\]]+)\]\s"(?P<method>.*?)\s(?P<path>.*?)\s(?P<protocol>.*?)"\s(?P<status>\d+)\s(?P<size>\d+)\s"(?P<referer>.*?)"\s"(?P<user_agent>.*?)"'

redis_connect = redis.Redis(
    host="redis",
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB_N,
    ssl=True,
    ssl_cert_reqs="required",
    ssl_keyfile="logreader.key.pem",
    ssl_certfile="logreader.cert.pem",
    ssl_ca_certs=settings.SSL_CA_CERT
)

client = docker.from_env()
db = client.containers.get(settings.DB_CONTAINER)
smp_net = client.networks.get("smp").attrs["IPAM"]["Config"][0]["Subnet"].replace("0/24","")

user=list(filter(lambda x: re.match(r'RVN_DB_USER=.*', x),db.attrs["Config"]["Env"]))[0].replace("RVN_DB_USER=",'')
password=list(filter(lambda x: re.match(r'RVN_DB_PASS=.*', x),db.attrs["Config"]["Env"]))[0].replace("RVN_DB_PASS=",'')
host=db.attrs["Config"]["Hostname"]
port=list(db.attrs["Config"]["ExposedPorts"].keys())[0].replace('/tcp','')
database=list(filter(lambda x: re.match(r'RVN_DB_NAME=.*', x),db.attrs["Config"]["Env"]))[0].replace("RVN_DB_NAME=",'')
connection = psycopg2.connect(user=user, password=password, host=host, port=port, database=database)

