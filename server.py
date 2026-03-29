"""
PrivateShare - Servidor de Señalización en la Nube
Deploy gratis en Railway, Render, o Fly.io

Instalar: pip install websockets
Correr:   python cloud_server.py
"""
import asyncio
import json
import os
import logging
from collections import defaultdict

try:
    import websockets
    from websockets.server import serve
except ImportError:
    print("ERROR: pip install websockets")
    raise

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger()

# room_id -> set of (websocket, peer_id, nick)
rooms = defaultdict(set)
# ws -> info dict
clients = {}

async def handler(websocket):
    client_room = None
    client_id = None

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            t = msg.get('type')
            room = msg.get('room')
            frm  = msg.get('from')

            if not t:
                continue

            if t == 'ping':
                await websocket.send(json.dumps({'type':'pong'}))
                continue

            if t == 'room-join' and room and frm:
                # Salir de sala anterior
                if client_room:
                    rooms[client_room].discard(websocket)
                    if not rooms[client_room]:
                        del rooms[client_room]

                client_room = room
                client_id = frm
                rooms[room].add(websocket)
                clients[websocket] = {'id': frm, 'nick': msg.get('nick','?'), 'room': room}

                log.info(f"JOIN room={room} nick={msg.get('nick')} peers={len(rooms[room])}")
                await broadcast(room, raw, exclude=websocket)
                continue

            if t == 'room-leave':
                if client_room:
                    rooms[client_room].discard(websocket)
                    await broadcast(client_room, raw, exclude=websocket)
                    if not rooms[client_room]:
                        del rooms[client_room]
                    client_room = None
                continue

            # offer / answer / ice / stream-start / stream-stop
            to = msg.get('to')
            if to:
                await send_to(to, raw)
            elif room:
                await broadcast(room, raw, exclude=websocket)

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log.debug(f"client error: {e}")
    finally:
        if client_room:
            rooms[client_room].discard(websocket)
            # Notificar salida
            info = clients.get(websocket, {})
            leave = json.dumps({'type':'room-leave','from':info.get('id',''),'nick':info.get('nick',''),'room':client_room})
            await broadcast(client_room, leave)
            if not rooms[client_room]:
                del rooms[client_room]
        clients.pop(websocket, None)


async def broadcast(room, raw, exclude=None):
    targets = list(rooms.get(room, set()))
    for ws in targets:
        if ws is exclude:
            continue
        try:
            await ws.send(raw)
        except Exception:
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


async def main():
    port = int(os.environ.get('PORT', 8765))
    host = '0.0.0.0'
    log.info(f"PrivateShare Signaling Server → ws://{host}:{port}")
    
    async with serve(handler, host, port, ping_interval=20, ping_timeout=10):
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    asyncio.run(main())
