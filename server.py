"""
PrivateShare - Servidor unificado (HTTP + WebSocket)
Sirve el HTML Y gestiona la señalización WebSocket
Deploy en Render: gratis, siempre accesible por HTTPS/WSS
"""
import asyncio
import json
import os
import logging
import mimetypes
from pathlib import Path
from collections import defaultdict

import websockets
from websockets.server import serve

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger()

# ── Estado de salas ──────────────────────────────────────────
rooms   = defaultdict(set)   # room_id → set of websockets
clients = {}                  # ws → {id, nick, room}


# ── HTML embebido (se reemplaza en build) ────────────────────
HTML_FILE = Path(__file__).parent / 'app.html'


def get_html():
    if HTML_FILE.exists():
        return HTML_FILE.read_text(encoding='utf-8')
    return '<h1>app.html no encontrado</h1>'


# ── HTTP handler (sirve el HTML) ─────────────────────────────
async def http_handler(path, request_headers):
    """Responde a peticiones HTTP normales sirviendo el HTML"""
    # Render hace health checks en GET /
    if request_headers.get('Upgrade', '').lower() == 'websocket':
        return None  # dejar pasar al handler WS

    # Servir el HTML para cualquier ruta GET
    html = get_html()
    headers = {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Access-Control-Allow-Origin': '*',
    }
    return (200, headers, html.encode('utf-8'))


# ── WebSocket handler (señalización) ────────────────────────
async def ws_handler(websocket):
    client_room = None
    client_id   = None

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            t    = msg.get('type')
            room = msg.get('room')
            frm  = msg.get('from')

            if not t:
                continue

            if t == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
                continue

            if t == 'join' and room and frm:
                # Salir de sala anterior
                if client_room:
                    rooms[client_room].discard(websocket)
                    if not rooms[client_room]:
                        del rooms[client_room]

                client_room = room
                client_id   = frm
                rooms[room].add(websocket)
                clients[websocket] = {'id': frm, 'nick': msg.get('nick', '?'), 'room': room}

                n = len(rooms[room])
                log.info(f"JOIN  room={room:<8} nick={msg.get('nick','?'):<12} peers={n}")

                # Notificar a los demás en la sala
                await broadcast(room, raw, exclude=websocket)
                continue

            if t == 'leave':
                if client_room:
                    rooms[client_room].discard(websocket)
                    await broadcast(client_room, raw, exclude=websocket)
                    if not rooms[client_room]:
                        del rooms[client_room]
                    client_room = None
                continue

            # offer / answer / ice / stream-on / stream-off
            to = msg.get('to')
            if to:
                await send_to(to, raw)        # mensaje directo
            elif room:
                await broadcast(room, raw, exclude=websocket)  # broadcast sala

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log.debug(f"ws error: {e}")
    finally:
        if client_room:
            rooms[client_room].discard(websocket)
            info = clients.get(websocket, {})
            leave_msg = json.dumps({
                'type': 'leave',
                'from': info.get('id', ''),
                'nick': info.get('nick', ''),
                'room': client_room,
            })
            await broadcast(client_room, leave_msg)
            if not rooms[client_room]:
                del rooms[client_room]
        clients.pop(websocket, None)


async def broadcast(room, raw, exclude=None):
    targets = list(rooms.get(room, set()))
    dead = []
    for ws in targets:
        if ws is exclude:
            continue
        try:
            await ws.send(raw)
        except Exception:
            dead.append(ws)
    for ws in dead:
        rooms[room].discard(ws)
        clients.pop(ws, None)


async def send_to(peer_id, raw):
    for ws, info in list(clients.items()):
        if info.get('id') == peer_id:
            try:
                await ws.send(raw)
            except Exception:
                pass
            return


# ── Main ────────────────────────────────────────────────────
async def main():
    port = int(os.environ.get('PORT', 8765))
    log.info(f"PrivateShare server starting on port {port}")
    log.info(f"HTML file: {HTML_FILE} ({'found' if HTML_FILE.exists() else 'NOT FOUND'})")

    async with serve(
        ws_handler,
        host='0.0.0.0',
        port=port,
        process_request=http_handler,   # sirve HTTP Y WebSocket en el mismo puerto
        ping_interval=20,
        ping_timeout=15,
        max_size=10 * 1024 * 1024,      # 10MB max mensaje
    ):
        log.info(f"Ready → https://0.0.0.0:{port}")
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
