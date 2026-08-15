"""FastAPI WebSocket server for streaming screen frames."""

import asyncio
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from .capture import ScreenCapture

logger = logging.getLogger(__name__)

# Global references set by __main__.py before server starts
capture_engine: ScreenCapture | None = None
display_info: dict = {}
server_start_time: float = 0.0

# Track connected WebSocket clients
_connected_clients: set[str] = set()

app = FastAPI(title="LinuxExtend", version="1.0.0")


TEST_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinuxExtend - Stream Test</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            color: #e0e0e0;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            overflow: hidden;
        }
        .header {
            padding: 12px 20px;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #111;
            border-bottom: 1px solid #222;
            z-index: 10;
        }
        .header h1 {
            font-size: 16px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        .header h1 span { color: #4ecdc4; }
        .stats {
            display: flex;
            gap: 16px;
            font-size: 12px;
            font-variant-numeric: tabular-nums;
        }
        .stat { display: flex; align-items: center; gap: 4px; }
        .stat-label { color: #666; }
        .stat-value { color: #ccc; font-weight: 500; }
        .dot {
            width: 6px; height: 6px;
            border-radius: 50%;
            background: #444;
            transition: background 0.3s;
        }
        .dot.connected { background: #4ecdc4; box-shadow: 0 0 6px #4ecdc455; }
        .dot.error { background: #e74c3c; }
        .canvas-container {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 8px;
        }
        canvas {
            max-width: 100%;
            max-height: calc(100vh - 52px);
            background: #111;
            border-radius: 4px;
        }
        .overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: #666;
        }
        .overlay .icon { font-size: 48px; margin-bottom: 12px; }
        .overlay .msg { font-size: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ Linux<span>Extend</span></h1>
        <div class="stats">
            <div class="stat">
                <div class="dot" id="statusDot"></div>
                <span class="stat-value" id="statusText">Connecting</span>
            </div>
            <div class="stat">
                <span class="stat-label">FPS</span>
                <span class="stat-value" id="fpsValue">0</span>
            </div>
            <div class="stat">
                <span class="stat-label">Frame</span>
                <span class="stat-value" id="sizeValue">—</span>
            </div>
            <div class="stat">
                <span class="stat-label">Res</span>
                <span class="stat-value" id="resValue">—</span>
            </div>
        </div>
    </div>

    <div class="canvas-container">
        <canvas id="screenCanvas"></canvas>
        <div class="overlay" id="overlay">
            <div class="icon">📡</div>
            <div class="msg">Connecting to stream...</div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('screenCanvas');
        const overlay = document.getElementById('overlay');
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const fpsValue = document.getElementById('fpsValue');
        const sizeValue = document.getElementById('sizeValue');
        const resValue = document.getElementById('resValue');

        let ctx = null;
        let frameCount = 0;
        let lastFpsTime = performance.now();
        let ws = null;

        function formatBytes(bytes) {
            if (bytes < 1024) return bytes + ' B';
            return (bytes / 1024).toFixed(1) + ' KB';
        }

        function updateFps() {
            const now = performance.now();
            const elapsed = (now - lastFpsTime) / 1000;
            if (elapsed >= 1.0) {
                fpsValue.textContent = Math.round(frameCount / elapsed);
                frameCount = 0;
                lastFpsTime = now;
            }
        }

        function connect() {
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = proto + '//' + location.host + '/ws/screen';

            ws = new WebSocket(wsUrl);
            ws.binaryType = 'blob';

            ws.onopen = () => {
                statusDot.className = 'dot connected';
                statusText.textContent = 'Connected';
                overlay.style.display = 'none';
            };

            ws.onmessage = async (event) => {
                try {
                    sizeValue.textContent = formatBytes(event.data.size);

                    const bitmap = await createImageBitmap(event.data);

                    if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
                        canvas.width = bitmap.width;
                        canvas.height = bitmap.height;
                        resValue.textContent = bitmap.width + '×' + bitmap.height;
                        // Use bitmaprenderer for zero-copy if available
                        ctx = canvas.getContext('bitmaprenderer');
                        if (!ctx) {
                            ctx = canvas.getContext('2d');
                        }
                    }

                    if (ctx.transferFromImageBitmap) {
                        ctx.transferFromImageBitmap(bitmap);
                    } else {
                        ctx.drawImage(bitmap, 0, 0);
                        bitmap.close();
                    }

                    frameCount++;
                    updateFps();
                } catch (e) {
                    console.error('Frame decode error:', e);
                }
            };

            ws.onclose = () => {
                statusDot.className = 'dot';
                statusText.textContent = 'Disconnected';
                overlay.style.display = '';
                overlay.querySelector('.msg').textContent = 'Connection lost. Reconnecting...';
                setTimeout(connect, 2000);
            };

            ws.onerror = () => {
                statusDot.className = 'dot error';
                statusText.textContent = 'Error';
            };
        }

        connect();
    </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def test_page() -> str:
    """Serve a browser-based test page for the screen stream."""
    return TEST_PAGE_HTML


@app.get("/status")
async def status() -> JSONResponse:
    """Health check endpoint with server info."""
    fps = capture_engine.actual_fps if capture_engine else 0
    return JSONResponse({
        "status": "running",
        "display": display_info,
        "capture": {
            "fps": fps,
            "running": capture_engine.is_running if capture_engine else False,
        },
        "clients": len(_connected_clients),
        "uptime_seconds": round(time.time() - server_start_time, 1),
    })


@app.websocket("/ws/screen")
async def screen_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint that streams JPEG frames to connected clients."""
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    _connected_clients.add(client_id)
    logger.info("Client connected: %s (total: %d)", client_id, len(_connected_clients))

    try:
        frame_interval = capture_engine.frame_interval if capture_engine else 0.04
        last_frame: bytes | None = None

        while True:
            if capture_engine is None:
                await asyncio.sleep(1)
                continue

            frame = capture_engine.get_frame()

            # Only send if we have a new frame (avoid duplicate sends)
            if frame is not None and frame is not last_frame:
                await websocket.send_bytes(frame)
                last_frame = frame

            await asyncio.sleep(frame_interval)

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", client_id)
    except Exception as e:
        logger.warning("Client %s error: %s", client_id, e)
    finally:
        _connected_clients.discard(client_id)
        logger.info("Client removed: %s (remaining: %d)", client_id, len(_connected_clients))
