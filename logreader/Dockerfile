FROM python:3.13.3-alpine3.21

ARG UNAME=appuser \
    UID=1111 \
    GID=444

ARG https_proxy=http://proxy:3128
ARG http_proxy=http://proxy:3128

ENV PATH="/home/$UNAME/.local/bin:$PATH" \
    FLASK_APP="app.py" \
    FLASK_ENV="production" \
    PYTHONUNBUFFERED=1

RUN addgroup --gid $GID $UNAME && \
    adduser --disabled-password --ingroup "$UNAME" --uid $UID $UNAME && \
    mkdir /data && mkdir /db && \
    chown $UID:$GID /data && chown $UID:$GID /db

RUN apk update && apk add --no-cache \
    postgresql-dev \
    ca-certificates

COPY --chown=$UID:$GID ca.cert.pem /usr/local/share/ca-certificates/
RUN update-ca-certificates

USER $UNAME

WORKDIR /app

COPY --chown=$UID:$GID requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY --chown=$UID:$GID . .

CMD ["python3", "app.py"]
