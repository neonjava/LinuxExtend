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
        html, body {
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
            color: #e0e0e0;
            font-family: system-ui, -apple-system, sans-serif;
            touch-action: none;
            user-select: none;
        }
        .header {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 44px;
            padding: 0 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(10, 10, 10, 0.85);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            z-index: 50;
            transition: opacity 0.3s ease, transform 0.3s ease;
        }
        .header.hidden {
            opacity: 0;
            transform: translateY(-100%);
            pointer-events: none;
        }
        .header h1 {
            font-size: 14px;
            font-weight: 600;
        }
        .header h1 span { color: #4ecdc4; }
        .stats {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 11px;
        }
        .fullscreen-btn {
            background: #4ecdc4;
            border: none;
            color: #002220;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .stat { display: flex; align-items: center; gap: 4px; }
        .dot {
            width: 6px; height: 6px;
            border-radius: 50%;
            background: #444;
        }
        .dot.connected { background: #4ecdc4; box-shadow: 0 0 6px #4ecdc4; }
        .canvas-container {
            width: 100vw;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #000;
            contain: strict;
            overflow: hidden;
        }
        canvas {
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: #000;
            image-rendering: -webkit-optimize-contrast;
            image-rendering: pixelated;
            transform: translateZ(0);
            backface-visibility: hidden;
            will-change: transform;
        }
        .overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: #888;
            pointer-events: none;
        }
        .overlay .icon { font-size: 40px; margin-bottom: 8px; }
        .overlay .msg { font-size: 13px; }
    </style>
</head>
<body>
    <div class="header" id="header">
        <h1>🖥️ Linux<span>Extend</span></h1>
        <div class="stats">
            <button class="fullscreen-btn" id="fsBtn" onclick="toggleFullscreen()">
                ⛶ Tap for Fullscreen
            </button>
            <div class="stat">
                <div class="dot" id="statusDot"></div>
                <span id="fpsValue">0 FPS</span>
            </div>
        </div>
    </div>

    <div class="canvas-container" id="container" onclick="handleTap()">
        <canvas id="screenCanvas"></canvas>
        <div class="overlay" id="overlay">
            <div class="icon">📡</div>
            <div class="msg">Connecting to LinuxExtend...</div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('screenCanvas');
        const overlay = document.getElementById('overlay');
        const header = document.getElementById('header');
        const statusDot = document.getElementById('statusDot');
        const fpsValue = document.getElementById('fpsValue');

        let ctx = null;
        let frameCount = 0;
        let lastFpsTime = performance.now();
        let ws = null;
        let hideTimeout = null;
        let pendingBitmap = null;

        function toggleFullscreen() {
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                if (document.documentElement.requestFullscreen) {
                    document.documentElement.requestFullscreen();
                } else if (document.documentElement.webkitRequestFullscreen) {
                    document.documentElement.webkitRequestFullscreen();
                }
                header.classList.add('hidden');
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }
                header.classList.remove('hidden');
            }
        }

        document.addEventListener('fullscreenchange', () => {
            if (document.fullscreenElement) {
                header.classList.add('hidden');
            } else {
                header.classList.remove('hidden');
            }
        });

        function handleTap() {
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                toggleFullscreen();
            } else {
                if (header.classList.contains('hidden')) {
                    header.classList.remove('hidden');
                    clearTimeout(hideTimeout);
                    hideTimeout = setTimeout(() => {
                        if (document.fullscreenElement) header.classList.add('hidden');
                    }, 3000);
                } else {
                    header.classList.add('hidden');
                }
            }
        }

        function updateFps() {
            const now = performance.now();
            const elapsed = (now - lastFpsTime) / 1000;
            if (elapsed >= 1.0) {
                if (fpsValue) fpsValue.textContent = Math.round(frameCount / elapsed) + ' FPS';
                frameCount = 0;
                lastFpsTime = now;
            }
        }

        // Hardware-synchronized requestAnimationFrame render loop
        function renderLoop() {
            if (pendingBitmap && ctx) {
                if (ctx.transferFromImageBitmap) {
                    ctx.transferFromImageBitmap(pendingBitmap);
                } else {
                    ctx.drawImage(pendingBitmap, 0, 0);
                    pendingBitmap.close();
                }
                pendingBitmap = null;
                frameCount++;
                updateFps();
            }
            requestAnimationFrame(renderLoop);
        }
        requestAnimationFrame(renderLoop);

        function connect() {
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = proto + '//' + location.host + '/ws/screen';

            ws = new WebSocket(wsUrl);
            ws.binaryType = 'blob';

            ws.onopen = () => {
                if (statusDot) statusDot.className = 'dot connected';
                overlay.style.display = 'none';
            };

            ws.onmessage = async (event) => {
                try {
                    overlay.style.display = 'none';
                    // Fast hardware-accelerated decode without alpha/colorspace conversion overhead
                    const bitmap = await createImageBitmap(event.data, {
                        premultiplyAlpha: 'none',
                        colorSpaceConversion: 'none',
                    });

                    if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
                        canvas.width = bitmap.width;
                        canvas.height = bitmap.height;
                        ctx = canvas.getContext('bitmaprenderer', { alpha: false }) || canvas.getContext('2d', { alpha: false });
                    }

                    if (pendingBitmap) {
                        pendingBitmap.close();
                    }
                    pendingBitmap = bitmap;
                } catch (e) {
                    console.error('Frame decode error:', e);
                }
            };

            ws.onclose = () => {
                if (statusDot) statusDot.className = 'dot';
                overlay.style.display = '';
                overlay.querySelector('.msg').textContent = 'Reconnecting...';
                setTimeout(connect, 1500);
            };

            ws.onerror = () => {
                if (statusDot) statusDot.className = 'dot error';
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
        client_last_frame_id = -1

        while True:
            if capture_engine is None:
                await asyncio.sleep(0.1)
                continue

            frame, frame_id = capture_engine.get_frame_with_id()

            # Send immediately if a newer frame is available
            if frame is not None and frame_id != client_last_frame_id:
                await websocket.send_bytes(frame)
                client_last_frame_id = frame_id
                await asyncio.sleep(0.008)  # Sub-10ms yield
            else:
                await asyncio.sleep(0.005)  # Fast poll for next frame

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", client_id)
    except Exception as e:
        logger.warning("Client %s error: %s", client_id, e)
    finally:
        _connected_clients.discard(client_id)
        logger.info("Client removed: %s (remaining: %d)", client_id, len(_connected_clients))
