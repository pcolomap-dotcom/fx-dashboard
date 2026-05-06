# 💱 FX Dashboard — CLP/EUR · USD/EUR · CLP/USD

Dashboard de tipos de cambio con histórico de 30 días, tendencias y márgenes
(`media ± σ`) sugeridos para compra/venta. **Web pública, gratis, sin servidor.**

Datos: [mindicador.cl](https://mindicador.cl) (Banco Central de Chile),
con fallback a [api.frankfurter.app](https://api.frankfurter.app) (BCE).
Hosting: GitHub Pages. Refresh diario automático vía GitHub Actions.

---

## 🚀 Publicarlo (5 minutos, sin terminal)

### 1. Crear repo en GitHub

1. Entra en [github.com](https://github.com) (crea cuenta gratis si no tienes).
2. Arriba a la derecha → **+** → **New repository**.
3. Nombre: `fx-dashboard` (o el que quieras). **Public**. → **Create repository**.

### 2. Subir los archivos

En la página del repo recién creado:

1. Click **uploading an existing file** (en el texto del centro).
2. Arrastra **estos archivos** desde `C:\proyectos\mi-primer-proyecto\`:
   - `fx_dashboard.py`
   - `icon.svg`
   - `README.md`
   - `.gitignore`
3. Para el workflow tienes que respetar la ruta `.github/workflows/deploy.yml`:
   - En el campo de nombre del archivo (arriba) escribe literalmente
     `.github/workflows/deploy.yml` y pega el contenido. GitHub creará las carpetas.
   - O sube `deploy.yml` y luego renómbralo. Más fácil: hazlo desde la web,
     **Add file → Create new file**, nombre `.github/workflows/deploy.yml`, pega contenido.
4. Abajo: **Commit changes**.

### 3. Activar GitHub Pages

1. En el repo: **Settings** (pestaña arriba) → **Pages** (menú izquierdo).
2. **Source:** elige **GitHub Actions**. Ya está.

### 4. Esperar el primer deploy

1. Pestaña **Actions** del repo → verás el workflow `Build & Deploy FX Dashboard` corriendo.
2. Cuando ponga ✅ verde (~1–2 min), tu URL está lista en:

   ```
   https://<tu-usuario>.github.io/fx-dashboard/
   ```

3. Si no se lanzó solo, pestaña **Actions** → workflow → **Run workflow**.

---

## 📱 Instalar en iPhone

1. Abre la URL en **Safari** (Chrome no permite esto en iOS).
2. Botón **Compartir** (cuadrado con flecha hacia arriba).
3. **Añadir a pantalla de inicio** → **Añadir**.
4. Aparece como icono `💱 FX` en tu home como una app más.

Tras eso se abre en pantalla completa, sin barra del navegador.

## 👯 Compartir con amigos

Manda el link por WhatsApp/Telegram. Que repitan el paso "Añadir a pantalla de inicio".
No necesitan cuenta de nada.

---

## ⏰ Actualización automática

GitHub Actions ejecuta el script **a las 16:30 UTC de lunes a viernes**
(después de la publicación diaria del BCE), regenera el HTML y lo despliega.

Para forzar un refresh manual: pestaña **Actions** → workflow → **Run workflow**.

Para cambiar la frecuencia: edita el `cron` en `.github/workflows/deploy.yml`.

---

## 🛠️ Desarrollo local

Genera el dashboard en tu PC sin desplegar:

```powershell
python fx_dashboard.py                 # genera dashboard.html y lo abre
python fx_dashboard.py --dias 60       # ventana de 60 días
python fx_dashboard.py --no-abrir      # solo genera el archivo
```

Sin dependencias externas — solo Python 3.10+ stdlib.

---

## 📂 Archivos del proyecto

| Archivo | Para qué |
|---|---|
| `fx_dashboard.py` | Script: descarga datos, calcula stats, genera HTML |
| `icon.svg` | Icono que aparece al añadir a pantalla de inicio |
| `.github/workflows/deploy.yml` | Acción que regenera y despliega cada día |
| `.gitignore` | Ignora HTML local generado en pruebas |
| `fx_app.py` *(opcional)* | Versión Streamlit para correr en local con sliders |

---

## ⚠️ Aviso

Análisis técnico básico (mean reversion sobre `μ ± σ`). **No es asesoría financiera.**
Las bandas son referencia estadística, no predicción.
