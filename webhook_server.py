#!/usr/bin/env python3
from aiohttp import web
import os
import json
import asyncio
from datetime import datetime

SECRET = os.getenv("WEBHOOK_SECRET", "your_secret")
ai_instance = None  # Будет установлен из run.py

async def status(request):
    if ai_instance:
        return web.json_response(ai_instance.get_status())
    return web.json_response({"error": "AI not initialized"}, status=500)

async def kill_switch(request):
    if ai_instance:
        await ai_instance.manual_kill_switch(True, "webhook")
        return web.json_response({"status": "kill_switch_activated"})
    return web.json_response({"error": "AI not initialized"}, status=500)

async def flatten(request):
    if ai_instance:
        result = await ai_instance.emergency_flatten()
        return web.json_response(result)
    return web.json_response({"error": "AI not initialized"}, status=500)

async def health(request):
    return web.json_response({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "ai_initialized": ai_instance is not None
    })

app = web.Application()
app.router.add_get("/status", status)
app.router.add_post("/kill", kill_switch)
app.router.add_post("/flatten", flatten)
app.router.add_get("/health", health)

def start_webhook():
    port = int(os.getenv("WEBHOOK_PORT", 9000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    start_webhook()
