
import os, asyncio, json, uvicorn
from config import redis_connect
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.templating import Jinja2Templates

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(root_path="/online")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.mount('/static', StaticFiles(directory=os.path.join(ROOT_PATH, "static")), 'static')
templates = Jinja2Templates(directory=[f"{ROOT_PATH}/templates",])
clients = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    await asyncio.sleep(1)
    for user in redis_connect.keys("*"):
        user_data = json.loads(redis_connect.get(user).decode("utf-8"))
        data = {
            "ip": user_data[1],
            "timestamp": user_data[2]
        }
        await websocket.send_json(data)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        clients.remove(websocket)

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})

@app.post("/data/update")
async def update_data(data: dict):
    for client in list(clients):
        try:
            await client.send_json(data)
        except:
            clients.remove(client)
