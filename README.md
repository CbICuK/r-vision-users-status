# r-vision-users-status

Отображение активных статусов пользователей системы.

Сервисы:

## 1. Log reader

Считывает лог веб-сервера в реальном времени. Формат лога задается через регулярное выражение в файле config.py

```python
LOG_PARSER_REGEX=r'(::ffff:|)(?P<ip>\d+\.\d+\.\d+\.\d+)\s-\s-\s\[(?P<time>[^\]]+)\]\s"(?P<method>.*?)\s(?P<path>.*?)\s(?P<protocol>.*?)"\s(?P<status>\d+)\s(?P<size>\d+)\s"(?P<referer>.*?)"\s"(?P<user_agent>.*?)"'
```
## 2. Status page


## 3. Redis