# R-Vision users status

Отображение активных статусов пользователей системы.
Данные собираются с веб-сервера. Лог содержит только ip-адреса польщователей 

## Сервисы:

### 1. Log reader

Считывает лог веб-сервера в реальном времени. Формат лога задается через регулярное выражение в файле config.py

```python
LOG_PARSER_REGEX=r'(::ffff:|)(?P<ip>\d+\.\d+\.\d+\.\d+)\s-\s-\s\[(?P<time>[^\]]+)\]\s"(?P<method>.*?)\s(?P<path>.*?)\s(?P<protocol>.*?)"\s(?P<status>\d+)\s(?P<size>\d+)\s"(?P<referer>.*?)"\s"(?P<user_agent>.*?)"'
```
### 2. Status page

Веб страница для отображения статусов. 
Переход статусов по цветам зеленый -> оранжевый -> серый.
От зеленого к оранжевому за 1 час.
От оранжевого к серому за 23 часа.
Пользователи хранятся в базе 24 часа.

### 3. Redis

База для хранения актуальной информации.



## Подготовка
    
1. Предполагается размещение на том же сервере где установлен контейнер с nginx. Поэтому docker и docker-compose должны быть уже устаонвлены в системе.
2. Файл `.env` уже содержит необходимые переменные, но их можно переопределить при необходимости

```
REDIS_BROKER_HOST=redis # Имя хоста контейнера redis. Должен совпадать с тем что указанан в docker-compose.yml
REDIS_DB_N=1 # Номер базы redis, может быть любым от 1 до 16
REDIS_PORT=6379 # порт подключения к redis c tls. в redis.conf дополнительно указан порт 6380 для локального подключения без tls
REDIS_USER=redis_user # пользователь redis. по умолчанию не используется
REDIS_PASS=redis_pass # пароль redis. по умолчанию не используется
SSL_CA_CERT=CA.crt # корневой сертификат для общения сервисов друг с другом

WEB_NAME=web # Имя хоста контейнера status-page. Должен совпадать с тем что указанан в docker-compose.yml
WEB_PORT=9090 # Порт на котором запускается uvicorn

NGINX_CONTAINER=r-vision-lts-nginx-1 # Стандартное имя контейнера nginx для чтения логов
DB_CONTAINER=smp-db-lts-postgresql-1 # Стандартное имя контейнера БД. Нужно, для сопоставления IP c именем пользователя

```

## Установка

>[!IMPORTANT]
>Т.к. текцщему приложению необходим доступ к контейнерам, находящися в сети SMP r-vison, то обязательно сначала нужно запустить приложение и только после этого добавлять новый эндпоинт в r-vision.
>В противном случае контейнер с nginx не запустится.

1. Разместить файлы репозитория в одном каталоге, например `/opt/users-online/`
2. Перейти в каталог и собрать образы
```bash
cd /opt/users-online/ && docker-compose build
```
3. Запустить контейнеры
```bash
docker-compose up -d
```
4. Размесить в каталоге `/opt/r-vision/data/smp/volumes/nginx/` файл `online.location`
```conf
    location /online/static/ {
      proxy_set_header   Host             $host;
      proxy_set_header   X-Real-IP        $remote_addr;
      proxy_set_header   X-Forwarded-For  $proxy_add_x_forwarded_for;
      proxy_set_header   X-Forwarded-Proto $scheme;
      proxy_pass http://web:9090;
    }


    location /online/ {
      proxy_set_header   Host             $host;
      proxy_set_header   X-Real-IP        $remote_addr;
      proxy_set_header   X-Forwarded-For  $proxy_add_x_forwarded_for;
      proxy_set_header   X-Forwarded-Proto $scheme;
      proxy_pass http://web:9090/;
      proxy_http_version 1.1;
      proxy_set_header   Upgrade $http_upgrade;
      proxy_set_header   Connection "upgrade";
      proxy_set_header   Content-Security-Policy "upgrade-insecure-requests";
    }
```
5. Перезапустить контейнеры 
```bash
cd /opt/r-vision/utils/ && ./down-all.sh && ./up-all.sh
```
6. Проверить, что контейнер с nginx запустился 
```bash
docker logs -n 10 -f r-vision-lts-nginx-1
```

## Использование 

Страница с монторингом доступна по ссылке `http(s)://<FQDN вашего сервера>/online`