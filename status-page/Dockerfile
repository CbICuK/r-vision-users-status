FROM python:3.13.3-alpine3.21

ARG UNAME=appuser \
    UID=1111 \
    GID=1111

ARG https_proxy=http://proxy:3128 
ARG http_proxy=http://proxy:3128

ENV PATH="/home/$UNAME/.local/bin:$PATH" \
    FLASK_APP="app.py" \
    FLASK_ENV="production" \
    PYTHONUNBUFFERED=1

RUN addgroup --gid $GID $UNAME && \
    adduser --disabled-password --ingroup "$UNAME" --uid $UID $UNAME

RUN apk update && apk add --no-cache \
    ca-certificates 

COPY --chown=$UID:$GID ca.cert.pem /usr/local/share/ca-certificates/
RUN update-ca-certificates

USER $UNAME

WORKDIR /app

COPY --chown=$UID:$GID requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY --chown=$UID:$GID . .

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "9090", "--log-level", "error", "--proxy-headers", "--forwarded-allow-ips", "*", "--ws", "auto", "app:app"]
