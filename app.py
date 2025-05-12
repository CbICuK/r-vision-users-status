
import docker
import re
from config import Settings
import asyncio
import sys
from collections import deque
from typing import List, Dict
from flask_socketio import SocketIO, emit
from flask import Flask, request
# 10.10.10.10 - - [12/May/2025:12:18:47 +0000] "GET /api/v1/im/incidents/318308/view?_dc=1747052336284 HTTP/1.1" 200 83 "https://10.0.0.1/" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 YaBrowser/24.7.0.0 Safari/537.36"
# Регулярное выражение для парсинга логов Nginx (Combined Log Format)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

async def parse_nginx_logs(container_name: str, buffer_size: int = 100, buffer_timeout: float = 1.0):
    try:
        # Подключаемся к Docker API
        client = docker.from_env()
        container = client.containers.get(container_name)

        # Регулярное выражение для парсинга логов Nginx (формат combined)
        log_pattern = re.compile(r'(::ffff:|)(?P<ip>\d+\.\d+\.\d+\.\d+)\s-\s-\s\[(?P<time>[^\]]+)\]\s"(?P<method>.*?)\s(?P<path>.*?)\s(?P<protocol>.*?)"\s(?P<status>\d+)\s(?P<size>\d+)\s"(?P<referer>.*?)"\s"(?P<user_agent>.*?)"')

        # Буфер для накопления логов
        log_buffer: List[str] = deque(maxlen=buffer_size)
        last_flush = asyncio.get_event_loop().time()

        async def process_buffer(buffer: List[str]) -> None:
            """Асинхронная обработка накопленных логов."""
            for log_line in buffer:
                match = log_pattern.match(log_line)
                if match:
                    log_data = match.groupdict()
                    print(
                        f"IP: {log_data['ip']}, "
                        f"Time: {log_data['time']}, "
                        f"Method: {log_data['method']}, "
                        f"Path: {log_data['path']}, "
                        f"Protocol: {log_data['protocol']}, "
                        f"Status: {log_data['status']}, "
                        f"Size: {log_data['size']}"
                        f"Referer: {log_data['referer']}"
                        f"User-Agent: {log_data['user_agent']}"
                    )
                    socketio.emit("user_activity", {
                        "ip": log_data['ip'],
                        "timestamp": log_data['time']
                    });
                    
                    if int(log_data['status']) >= 500:
                        print("Обнаружена ошибка сервера!")
                        # Пример: отправка алерта или запись в базу данных
                        # await send_alert(log_data)
                else:
                    print(f"Строка не соответствует формату: {log_line}")
            buffer.clear()

        # Чтение логов в реальном времени
        for line in container.logs(stream=True, follow=True, tail=0):
            log_line = line.decode('utf-8').strip()
            if not log_line:
                continue

            # Добавляем строку в буфер
            log_buffer.append(log_line)

            # Проверяем условия для обработки буфера
            current_time = asyncio.get_event_loop().time()
            if len(log_buffer) >= buffer_size or (current_time - last_flush) >= buffer_timeout:
                await process_buffer(log_buffer)
                last_flush = current_time

            # Небольшая задержка для предотвращения блокировки
            await asyncio.sleep(0.2)

        # Обрабатываем оставшиеся логи в буфере
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
    container = Settings.CONTAINERNAME  # Имя целевого контейнера
    await parse_nginx_logs(
        container,
        buffer_size=100,  # Максимальный размер буфера (количество строк)
        buffer_timeout=1.0  # Максимальное время ожидания перед обработкой буфера (в секундах)
    )

if __name__ == "__main__":
    asyncio.run(main())
