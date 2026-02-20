#!/usr/bin/env python3
"""NERV Interface v0.3 — Full agent session access via Gateway WebSocket.
Uses chat.send for real agent runs (tools, files, commands, memory).
"""

import asyncio
import json
import os
import uuid
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn
import websockets

# Config
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 18789
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
TTYD_HOST = "192.168.8.124"
TTYD_PORT = 7681
NERV_PORT = 8080
NERV_SESSION_KEY = "agent:main:nerv"

app = FastAPI(title="NERV Interface")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

UPLOAD_DIR = Path.home() / ".openclaw" / "workspace" / "nerv-uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/config")
async def config():
    return {
        "ttyd_url": f"http://{TTYD_HOST}:{TTYD_PORT}",
        "ws_url": f"ws://{{host}}:{NERV_PORT}/ws/chat",
    }


async def create_gateway_ws():
    """Create an authenticated Gateway WebSocket connection."""
    headers = {"Origin": "http://127.0.0.1:8080"}
    ws = await websockets.connect(
        f"ws://{GATEWAY_HOST}:{GATEWAY_PORT}",
        max_size=10 * 1024 * 1024,
        additional_headers=headers,
    )
    
    # Receive challenge
    await asyncio.wait_for(ws.recv(), timeout=5)
    
    # Connect handshake
    connect_msg = {
        "type": "req",
        "id": "connect-1",
        "method": "connect",
        "params": {
            "minProtocol": 3,
            "maxProtocol": 3,
            "client": {
                "id": "openclaw-control-ui",
                "version": "0.3",
                "platform": "linux",
                "mode": "webchat",
            },
            "role": "operator",
            "scopes": ["operator.read", "operator.write", "operator.admin"],
            "caps": [],
            "commands": [],
            "permissions": {},
            "auth": {"token": GATEWAY_TOKEN},
            "locale": "en-US",
            "userAgent": "nerv-interface/0.3",
        },
    }
    await ws.send(json.dumps(connect_msg))
    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    
    if not resp.get("ok"):
        raise Exception(f"Gateway connect failed: {resp.get('error')}")
    
    return ws


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    """WebSocket bridge: NERV client <-> OpenClaw Gateway agent session."""
    await websocket.accept()
    
    gw_ws = None
    try:
        # Connect to gateway
        try:
            gw_ws = await create_gateway_ws()
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": f"Cannot connect to OpenClaw gateway: {e}"
            }))
            return
        
        await websocket.send_text(json.dumps({
            "type": "system",
            "content": "Connected to OpenClaw Gateway (full agent access)"
        }))
        
        # Background task: listen to gateway events and forward to client
        current_run_id = None
        run_complete = asyncio.Event()
        
        async def gateway_listener():
            nonlocal current_run_id
            try:
                async for raw in gw_ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    
                    msg_type = msg.get("type")
                    
                    if msg_type == "event":
                        event_name = msg.get("event", "")
                        payload = msg.get("payload", {})
                        
                        if not isinstance(payload, dict):
                            continue
                        
                        session_key = payload.get("sessionKey", "")
                        run_id = payload.get("runId", "")
                        
                        # Only process events for our session
                        if session_key and session_key != NERV_SESSION_KEY:
                            continue
                        
                        if event_name == "agent":
                            stream = payload.get("stream", "")
                            data = payload.get("data", {})
                            
                            if stream == "assistant":
                                delta = data.get("delta", "")
                                if delta:
                                    await websocket.send_text(json.dumps({
                                        "type": "chunk",
                                        "content": delta
                                    }))
                            
                            elif stream == "tool":
                                tool_name = data.get("name", "")
                                phase = data.get("phase", "")
                                
                                if phase == "start":
                                    await websocket.send_text(json.dumps({
                                        "type": "tool_start",
                                        "tool": tool_name,
                                        "input": data.get("input", {})
                                    }))
                                elif phase == "end":
                                    await websocket.send_text(json.dumps({
                                        "type": "tool_end",
                                        "tool": tool_name,
                                        "status": data.get("status", "ok")
                                    }))
                            
                            elif stream == "lifecycle":
                                phase = data.get("phase", "")
                                if phase == "end":
                                    await websocket.send_text(json.dumps({
                                        "type": "done"
                                    }))
                                    current_run_id = None
                                    run_complete.set()
                        
                        elif event_name == "chat":
                            state = payload.get("state", "")
                            
                            if state == "delta":
                                message = payload.get("message", {})
                                content = message.get("content", [])
                                for block in (content if isinstance(content, list) else []):
                                    if block.get("type") == "text":
                                        # Already handled by agent stream
                                        pass
                            
                            elif state == "final":
                                # Final message — ensure done is sent
                                if current_run_id:
                                    await websocket.send_text(json.dumps({
                                        "type": "done"
                                    }))
                                    current_run_id = None
                                    run_complete.set()
                    
                    elif msg_type == "res":
                        # Handle response to chat.send
                        payload = msg.get("payload", {})
                        if isinstance(payload, dict):
                            status = payload.get("status", "")
                            if status == "started":
                                current_run_id = payload.get("runId")
                            elif status == "error":
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "content": payload.get("error", "Run failed")
                                }))
                                run_complete.set()
                        
                        if not msg.get("ok") and msg.get("error"):
                            err = msg.get("error", {})
                            err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": err_msg
                            }))
                            run_complete.set()
            
            except websockets.exceptions.ConnectionClosed:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": "Gateway connection lost"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": f"Gateway listener error: {e}"
                }))
        
        # Start gateway listener
        listener_task = asyncio.create_task(gateway_listener())
        
        # Track if this is first message in session (needs boot context)
        is_first_message = True
        
        # Main loop: receive from NERV client, forward to gateway
        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                user_text = msg.get("content", "")
                
                if not user_text:
                    continue
                
                run_complete.clear()
                
                # First message flag (reserved for future use)
                if is_first_message:
                    is_first_message = False
                
                # Send via chat.send for full agent session
                idempotency_key = f"nerv-{uuid.uuid4().hex[:12]}"
                chat_req = {
                    "type": "req",
                    "id": idempotency_key,
                    "method": "chat.send",
                    "params": {
                        "sessionKey": NERV_SESSION_KEY,
                        "message": user_text,
                        "deliver": False,
                        "idempotencyKey": idempotency_key,
                    },
                }
                await gw_ws.send(json.dumps(chat_req))
        
        except WebSocketDisconnect:
            pass
        finally:
            listener_task.cancel()
    
    finally:
        if gw_ws:
            await gw_ws.close()


@app.get("/api/status")
async def get_status():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(
                f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/tools/invoke",
                headers={
                    "Authorization": f"Bearer {GATEWAY_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={"tool": "session_status", "args": {}},
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}


@app.get("/api/sessions")
async def get_sessions():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(
                f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/tools/invoke",
                headers={
                    "Authorization": f"Bearer {GATEWAY_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={"tool": "sessions_list", "args": {"limit": 10, "messageLimit": 1}},
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}


@app.get("/api/system")
async def get_system_metrics():
    """Get system metrics via gateway tools."""
    import shutil
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # Get system info via gateway exec tool
            r = await client.post(
                f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/tools/invoke",
                headers={
                    "Authorization": f"Bearer {GATEWAY_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "tool": "exec", 
                    "args": {
                        "command": "echo CPU:$(grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$3+$4+$5)} END {print usage \"%\"}') RAM:$(free -h | awk '/^Mem:/ {print $3\"/\"$2}') UPTIME:$(uptime -p | sed 's/up //')"
                    }
                },
            )
            
            if r.status_code == 200:
                result = r.json()
                output = result.get("result", {}).get("output", "")
                
                # Parse the output
                metrics = {}
                if "CPU:" in output and "RAM:" in output:
                    parts = output.split()
                    for part in parts:
                        if part.startswith("CPU:"):
                            metrics["cpu"] = part.split(":", 1)[1]
                        elif part.startswith("RAM:"):
                            metrics["ram"] = part.split(":", 1)[1]
                        elif part.startswith("UPTIME:"):
                            metrics["uptime"] = " ".join(parts[parts.index(part):]).split(":", 1)[1]
                            break
                
                # Get disk usage for workspace
                workspace = Path.home() / ".openclaw" / "workspace"
                if workspace.exists():
                    total, used, free = shutil.disk_usage(workspace)
                    metrics["disk"] = f"{used // (1024**3)}GB / {total // (1024**3)}GB"
                else:
                    metrics["disk"] = "—"
                
                return {"metrics": metrics}
            else:
                return {"error": "Failed to get system metrics"}
                
        except Exception as e:
            return {"error": str(e)}


@app.post("/api/switch-session")
async def switch_session(data: dict):
    """Switch the active session key."""
    global NERV_SESSION_KEY
    new_key = data.get("sessionKey")
    if not new_key:
        return {"error": "sessionKey required"}
    
    NERV_SESSION_KEY = new_key
    return {"success": True, "sessionKey": NERV_SESSION_KEY}


@app.get("/api/current-session")
async def get_current_session():
    """Get the current active session key."""
    return {"sessionKey": NERV_SESSION_KEY}


@app.get("/api/files")
async def list_files(path: str = ""):
    """List directory contents."""
    workspace = Path.home() / ".openclaw" / "workspace"
    
    if not path:
        target = workspace
    else:
        target = workspace / path.lstrip("/")
    
    # Security check - ensure we stay within workspace
    try:
        target = target.resolve()
        workspace = workspace.resolve()
        if not str(target).startswith(str(workspace)):
            return {"error": "Access denied"}
    except Exception:
        return {"error": "Invalid path"}
    
    if not target.exists():
        return {"error": "Path not found"}
    
    if not target.is_dir():
        return {"error": "Not a directory"}
    
    try:
        items = []
        for item in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            rel_path = str(item.relative_to(workspace))
            items.append({
                "name": item.name,
                "path": rel_path,
                "isDirectory": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime
            })
        
        return {"items": items, "currentPath": str(target.relative_to(workspace)) if target != workspace else ""}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/files/read")
async def read_file(path: str):
    """Read file content."""
    workspace = Path.home() / ".openclaw" / "workspace"
    target = workspace / path.lstrip("/")
    
    # Security check
    try:
        target = target.resolve()
        workspace = workspace.resolve()
        if not str(target).startswith(str(workspace)):
            return {"error": "Access denied"}
    except Exception:
        return {"error": "Invalid path"}
    
    if not target.exists():
        return {"error": "File not found"}
    
    if not target.is_file():
        return {"error": "Not a file"}
    
    try:
        # Check if file is too large
        if target.stat().st_size > 1024 * 1024:  # 1MB limit
            return {"error": "File too large (max 1MB)"}
        
        with open(target, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "content": content,
            "path": path,
            "size": target.stat().st_size,
            "modified": target.stat().st_mtime
        }
    except UnicodeDecodeError:
        return {"error": "Binary file - cannot display"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/file")
async def serve_file(path: str):
    """Serve a file for download/viewing."""
    workspace = Path.home() / ".openclaw" / "workspace"
    target = workspace / path.lstrip("/")
    
    # Security check
    try:
        target = target.resolve()
        workspace = workspace.resolve()
        if not str(target).startswith(str(workspace)):
            return {"error": "Access denied"}
    except Exception:
        return {"error": "Invalid path"}
    
    if not target.exists() or not target.is_file():
        return {"error": "File not found"}
    
    return FileResponse(str(target))


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    import shutil
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    ts = int(time.time())
    dest = UPLOAD_DIR / f"{ts}_{safe_name}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"path": str(dest), "filename": safe_name, "size": dest.stat().st_size}


@app.websocket("/ws/activity")
async def activity_ws(websocket: WebSocket):
    """Stream live agent activity from session log."""
    await websocket.accept()
    session_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
    
    try:
        while True:
            logs = sorted(
                [p for p in session_dir.glob("*.jsonl") if ".deleted" not in p.name and ".lock" not in p.name],
                key=lambda p: p.stat().st_mtime, reverse=True
            )
            if not logs:
                await asyncio.sleep(2)
                continue
            
            log_file = logs[0]
            with open(log_file, "r") as f:
                # Replay last 50 lines on connect for recent activity
                all_lines = f.readlines()
                replay_lines = all_lines[-50:] if len(all_lines) > 50 else all_lines
                for line in replay_lines:
                    await _process_activity_line(line, websocket)
                
                while True:
                    line = f.readline()
                    if not line:
                        await asyncio.sleep(0.3)
                        current_logs = sorted(
                            [p for p in session_dir.glob("*.jsonl") if ".deleted" not in p.name and ".lock" not in p.name],
                            key=lambda p: p.stat().st_mtime, reverse=True
                        )
                        if current_logs and current_logs[0] != log_file:
                            break
                        continue
                    
                    await _process_activity_line(line, websocket)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


async def _process_activity_line(line: str, websocket: WebSocket):
    """Parse a JSONL line and send tool call / thinking events to the activity feed."""
    try:
        entry = json.loads(line.strip())
        msg = entry.get("message", {})
        content = msg.get("content", "")
        role = msg.get("role", "")
        
        if isinstance(content, list):
            for block in content:
                btype = block.get("type", "")
                if btype == "toolCall":
                    tool_name = block.get("name", "unknown")
                    tool_input = block.get("input", {})
                    detail = ""
                    code = ""
                    if tool_name in ("Edit", "Write"):
                        fp = tool_input.get("file_path", tool_input.get("path", ""))
                        detail = f"FILE: {fp}"
                        if tool_name == "Edit":
                            code = tool_input.get("newText", tool_input.get("new_string", ""))[:500]
                        else:
                            code = tool_input.get("content", "")[:800]
                    elif tool_name == "exec":
                        detail = tool_input.get("command", "")[:300]
                    elif tool_name == "Read":
                        fp = tool_input.get("file_path", tool_input.get("path", ""))
                        detail = f"FILE: {fp}"
                    else:
                        detail = json.dumps(tool_input)[:200]
                    
                    await websocket.send_text(json.dumps({
                        "type": "tool_call",
                        "tool": tool_name,
                        "detail": detail,
                        "code": code,
                    }))
                
                elif btype == "text" and role == "assistant":
                    text = block.get("text", "")
                    if text.strip():
                        await websocket.send_text(json.dumps({
                            "type": "thinking",
                            "text": text[:300],
                        }))
    except (json.JSONDecodeError, KeyError):
        pass


if __name__ == "__main__":
    if not GATEWAY_TOKEN:
        print("⚠️  Set OPENCLAW_GATEWAY_TOKEN environment variable")
    uvicorn.run(app, host="0.0.0.0", port=NERV_PORT, log_level="info")
