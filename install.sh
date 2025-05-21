#!/bin/bash

if [ "$(id -u)" -ne 0 ]; then
    echo "Ошибка: для установки необходимы root-права. Запустите скрипт с помощью sudo."
    exit 1
fi

if ! command -v yq &> /dev/null; then
    if ! command -v wget &> /dev/null; then
        echo "Ошибка: wget не установлен. Установите wget и повторите попытку."
        exit 1
    fi

    wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq && chmod +x /usr/local/bin/yq
    echo "yq установлен."
else
    echo "yq уже установлен."
fi

DOCKER_GID=$(getent group docker | awk -F: '{print $3}')
DOCKER_COMPOSE_FILE="docker-compose.yml"
SERVICE_NAMES=($(yq '.services[].hostname' "$DOCKER_COMPOSE_FILE"))
SERVICE_FOLDERS=($(find . -maxdepth 1 -type d -not -name ".*" -and -not -name "certs" | awk '{gsub(/\.\/|\//,"");}1'))

NGINX_CONTAINER=$(docker ps -f label="com.docker.compose.service"="nginx" -f name="r-vision" --format '{{.Names}}')
DB_CONTAINER=$(docker ps -f label="com.docker.compose.service"="postgresql" -f name="smp" --format '{{.Names}}')
REDIS_BROKER_HOST=$(yq '.services[].hostname' "$DOCKER_COMPOSE_FILE" | grep redis)
WEB_NAME=$(yq '.services[].hostname' "$DOCKER_COMPOSE_FILE" | grep page)
SSL_CA_CERT="CA.crt"

if ! cat .env | grep NGINX_CONTAINER &> /dev/null; then
    echo "NGINX_CONTAINER=$NGINX_CONTAINER" >> ".env"
else
    sed -i "s/^NGINX_CONTAINER=.*$/NGINX_CONTAINER=$NGINX_CONTAINER/" ".env"
fi
if ! cat .env | grep DB_CONTAINER &> /dev/null; then
    echo "DB_CONTAINER=$DB_CONTAINER" >> ".env"
else
    sed -i "s/^DB_CONTAINER=.*$/DB_CONTAINER=$DB_CONTAINER/" ".env"
fi
if ! cat .env | grep REDIS_BROKER_HOST &> /dev/null; then
    echo "REDIS_BROKER_HOST=$REDIS_BROKER_HOST" >> ".env"
else
    sed -i "s/^REDIS_BROKER_HOST=.*$/REDIS_BROKER_HOST=$REDIS_BROKER_HOST/" ".env"
fi
if ! cat .env | grep SSL_CA_CERT &> /dev/null; then
    echo "SSL_CA_CERT=$SSL_CA_CERT" >> ".env"
else
    sed -i "s/^SSL_CA_CERT=.*$/SSL_CA_CERT=$SSL_CA_CERT/" ".env"
fi
if ! cat .env | grep WEB_NAME &> /dev/null; then
    echo "WEB_NAME=$WEB_NAME" >> ".env"
else
    sed -i "s/^WEB_NAME=.*$/WEB_NAME=$WEB_NAME/" ".env"
fi

set -e

if ! command -v openssl &> /dev/null; then
    echo "Ошибка: openssl не установлен."
    exit 1
fi

CERT_DIR="./certs"
mkdir -p "$CERT_DIR"

OPENSSL_CONF_TEMPLATE="$CERT_DIR/openssl_template.cnf"

cat > "$OPENSSL_CONF_TEMPLATE" <<EOF
[ req ]
default_bits       = 2048
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = req_ext

[ dn ]
C  = RU
ST = Moscow
L  = Moscow
O  = SYSA INC
OU = DIB
CN = DEFAULT_CN

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = DEFAULT_DNS

[ v3_ext ]
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names
EOF

echo "Создание корневого сертификата..."
openssl req -x509 -newkey rsa:4096 -days 3650 -nodes \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=SYSA INC/OU=DIB/CN=Root-CA" \
    -keyout "$CERT_DIR/ca.key.pem" -out "$CERT_DIR/ca.cert.pem" > /dev/null 2>&1


for FOLDER in "${SERVICE_FOLDERS[@]}"; do
    cp "$CERT_DIR/ca.cert.pem" "$FOLDER/CA.crt"
done

generate_cert() {
    NAME=$1
    CN=$2
    DNS_ALT=$3

    echo "Создание сертификата для $NAME (CN=$CN service, SAN=$DNS_ALT)..."

    CONF_FILE="$CERT_DIR/${NAME}.cnf"
    cp "$OPENSSL_CONF_TEMPLATE" "$CONF_FILE"
    sed -i "s/DEFAULT_CN/$CN/" "$CONF_FILE"
    sed -i "s/DEFAULT_DNS/$DNS_ALT/" "$CONF_FILE"

    openssl req -new -nodes -newkey rsa:2048 \
        -keyout "$CERT_DIR/${NAME}.key.pem" \
        -out "$CERT_DIR/${NAME}.csr.pem" \
        -config "$CONF_FILE" > /dev/null 2>&1

    openssl x509 -req -in "$CERT_DIR/${NAME}.csr.pem" \
        -CA "$CERT_DIR/ca.cert.pem" -CAkey "$CERT_DIR/ca.key.pem" -CAcreateserial \
        -out "$CERT_DIR/${NAME}.cert.pem" -days 825 \
        -extfile "$CONF_FILE" -extensions v3_ext > /dev/null 2>&1
    
}

echo "Найденные сервисы: ${SERVICE_NAMES[@]}"

for SERVICE in "${SERVICE_NAMES[@]}"; do
    CN="$(echo "$SERVICE service" | sed 's/-/ /g; s/\b\(.\)/\u\1/g')"  # Преобразуем имя в заглавный стиль
    generate_cert "$SERVICE" "$CN" "$SERVICE"
    mv "$CERT_DIR/${SERVICE}.cert.pem" "${SERVICE}/"
    mv "$CERT_DIR/${SERVICE}.key.pem" "${SERVICE}/"
done

echo "Все сертификаты успешно созданы в $CERT_DIR"

read -r -p "Используется ли прокси-сервер для подключения к сети интернет? [y/N]: " USE_PROXY

# Преобразуем ввод к нижнему регистру
USE_PROXY=${USE_PROXY,,}

# Проверим ответ
if [[ "$USE_PROXY" == "y" || "$USE_PROXY" == "yes" ]]; then
    read -r -p "Введите адрес и порт прокси-сервера (например, 10.10.10.10:3128 или proxy.example.com:8080): " PROXY_INPUT
    if [[ "$PROXY_INPUT" =~ ^([a-zA-Z0-9.-]+):([0-9]{2,5})$ ]]; then
        HOST="${BASH_REMATCH[1]}"
        PORT="${BASH_REMATCH[2]}"

        # Дополнительная проверка: порт в допустимых пределах
        if (( PORT >= 1 && PORT <= 65535 )); then
            for SERVICE in "${SERVICE_NAMES[@]}"; do
                if [ -f "$SERVICE/Dockerfile" ]; then
                    sed -i -E "s|^(ARG http_proxy=).*|\1http://$HOST:$PORT|" "$SERVICE/Dockerfile"
                    sed -i -E "s|^(ARG https_proxy=).*|\1http://$HOST:$PORT|" "$SERVICE/Dockerfile"
                fi
            done
        else
            echo "Ошибка: порт должен быть в диапазоне от 1 до 65535."
        fi
    else
        echo "Ошибка: укажите IP или FQDN и порт без протокола. Пример: 10.10.10.10:3128"
    fi
else
    for SERVICE in "${SERVICE_NAMES[@]}"; do
        if [ -f "$SERVICE/Dockerfile" ]; then
            sed -i '/s/^.*http_proxy.*$//' "$SERVICE/Dockerfile"
        fi
    done
fi

sed -E "s|^([[:space:]]*GID=)[0-9]+|\1$DOCKER_GID|" "logreader/Dockerfile"

docker-compose build
docker up -d
cp online.location /opt/r-vision/data/smp/volumes/nginx/
docker restart $NGINX_CONTAINER