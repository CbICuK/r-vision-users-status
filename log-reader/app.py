
import docker, re, asyncio, sys, requests, json
from config import redis_connect, settings, connection, smp_net, LOG_PARSER_REGEX
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from collections import deque
from typing import List
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_user_from_db(ip):
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT data->'values'->>'ip' as IP, data->'values'->>'user' as USER, "createdAt" as date FROM public.logs WHERE reference_table = 'users' AND data->>'template' = 'user_logged_in' AND data->'values'->>'ip' = %s ORDER BY "createdAt" DESC  LIMIT 1;""", (ip,))
            username = cursor.fetchone()
    return username

async def update(data: dict):
    requests.post(f"http://{settings.WEB_NAME}:{settings.WEB_PORT}/online/data/update", data=json.dumps(data),proxies={"http": "", "https": ""})

async def parse_nginx_logs(container_name: str, buffer_size: int = 100, buffer_timeout: float = 1.0):
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)

        log_pattern = re.compile(LOG_PARSER_REGEX)

        log_buffer: List[str] = deque(maxlen=buffer_size)
        last_flush = asyncio.get_event_loop().time()

        async def process_buffer(buffer: List[str]) -> None:
            for log_line in buffer:
                match = log_pattern.match(log_line)
                if match:
                    log_data = match.groupdict()
                    
                    date_time = datetime.strptime(log_data['time'], "%d/%B/%Y:%H:%M:%S %z")
                    
                    if log_data['ip'] != "127.0.0.1" and not log_data['ip'].startswith(smp_net) and not log_data['path'].startswith('/online'):
                        try:
                            if redis_connect.get(log_data['ip']):
                                user = json.loads(redis_connect.get(log_data['ip']).decode('utf-8'))
                                user[2] = datetime.strftime(date_time, "%Y-%m-%dT%H:%M:%S.%f%z")
                                redis_connect.set(user[0], json.dumps(user), ex=86400)
                                user = user[1]
                            else:
                                user = list(get_user_from_db(log_data['ip']))
                                last_date=datetime.strftime(user[2], "%Y-%m-%dT%H:%M:%S.%f%z")
                                user.pop(2)
                                user.append(last_date)
                                redis_connect.set(user[0], json.dumps(user), ex=86400)
                                user = user[1]
                        except Exception as e:
                            print(f"Error in redis_connect function: {e}")
                            pass

                        try:
                            await update(dict({
                                "ip": user,
                                "timestamp": datetime.strftime(date_time, "%Y-%m-%dT%H:%M:%S.%f%z")
                            }));
                        except Exception as e:
                            print(f"Error in update function: {e}")
                            pass
                    
                    if int(log_data['status']) >= 500:
                        print(f"Обнаружена ошибка сервера! Статус {log_data['status']}")
                else:
                    print(f"Строка не соответствует формату: {log_line}")
                    pass
            buffer.clear()

        for line in container.logs(stream=True, follow=True, tail=100):
            log_line = line.decode('utf-8').strip()
            if not log_line:
                continue

            log_buffer.append(log_line)

            current_time = asyncio.get_event_loop().time()
            if len(log_buffer) >= buffer_size or (current_time - last_flush) >= buffer_timeout:
                await process_buffer(log_buffer)
                last_flush = current_time

            await asyncio.sleep(0.2)

        if log_buffer:
            await process_buffer(log_buffer)

    except docker.errors.NotFound:
        print(f"Контейнер {container_name} не найден")
        sys.exit(1)
    except docker.errors.APIError as e:
        print(f"Ошибка Docker API: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Остановка обработки логов")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        sys.exit(1)

async def main():
    await parse_nginx_logs(settings.NGINX_CONTAINER, buffer_size=100, buffer_timeout=1.0)

if __name__ == "__main__":
    asyncio.run(main())
