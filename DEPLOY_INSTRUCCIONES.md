# 🌐 Cómo deployar tu servidor de señalización GRATIS

El servidor de señalización es lo que permite que vos y tus amigos se "encuentren"
antes de establecer la conexión directa. Solo necesita correr en algún lugar accesible
desde internet — lo cual Railway hace gratis en 2 minutos.

---

## OPCIÓN A — Railway (recomendado, más fácil)

**Tiempo: ~3 minutos | Costo: GRATIS**

1. Creá una cuenta en https://railway.app (podés entrar con GitHub)

2. En el dashboard, hacé click en **"New Project"**

3. Elegí **"Deploy from GitHub repo"** O **"Empty Project"**

4. Si elegís Empty Project:
   - Click en "Add a Service" → "Empty Service"
   - En la pestaña "Settings" → Source → subí la carpeta `cloud_server/`
   
5. **Forma más fácil** (sin GitHub):
   - Instalá Railway CLI: `npm install -g @railway/cli`
   - Desde la carpeta `cloud_server/`:
     ```
     railway login
     railway init
     railway up
     ```
   - Railway te da una URL como: `https://mi-app.railway.app`

6. Anotá tu URL (la necesitás en el siguiente paso)

---

## OPCIÓN B — Render (también gratis)

1. Creá cuenta en https://render.com

2. New → Web Service

3. Conectá con GitHub o subí el código manualmente

4. Configuración:
   - **Build Command**: `pip install websockets`
   - **Start Command**: `python server.py`
   - **Plan**: Free

5. Render te da URL: `https://mi-app.onrender.com`

---

## OPCIÓN C — Sin deploy (usar PeerJS/PubNub integrado)

La app YA incluye fallback automático a servidores públicos gratuitos
(PeerJS + PubNub) — funcionan para uso personal entre amigos.
No necesitás deployar nada propio para empezar.

---

## PASO FINAL — Conectar tu servidor a la app

Una vez que tengas tu URL de Railway/Render, abrí `src/app.html`
y buscá la línea cerca del principio del `<script>`:

```javascript
const BROKERS = [
  'wss://privateshare-signal.glitch.me',  // ← REEMPLAZÁ esto
  ...
```

Cambiala por tu URL:
```javascript
const BROKERS = [
  'wss://tu-app.railway.app',  // ← tu servidor propio
  ...
```

Después volvé a compilar el .exe con el script de build.

---

## ✅ Verificar que funciona

Abrí en el navegador: `https://tu-app.railway.app`

Debería verse algo como:
```
WebSocket server running
```

Si ves eso, el servidor está activo y listo.
