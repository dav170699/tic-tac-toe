# Agent Financial Advice — Estado del Proyecto

> Documento de continuación. Lee esto antes de retomar el trabajo.

---

## Qué es este proyecto

Agente Python que:
1. Monitorea noticias globales (NewsAPI, RSS), mercados (yfinance) y geopolítica (GDELT)
2. Analiza con Claude cuáles ETFs del PEA de BoursoBank (Amundi + iShares) conviene priorizar
3. Envía un newsletter estructurado por **email (Gmail/SendGrid)** y/o **WhatsApp (Twilio)**
4. Corre en local (Windows) o en servidor Linux (systemd) — mismo código, distinto despliegue

---

## Estado actual: ✅ Código completo — pendiente configurar claves

Todo el código está escrito y commiteado en GitHub. **El único paso que falta es crear el archivo `.env`** con las claves de API para poder ejecutar el agente.

### Lo que ya está listo
- [x] Estructura completa del proyecto (29 archivos)
- [x] `config/settings.yaml` — frecuencia, idioma, canal de entrega
- [x] `config/signal_map.yaml` — mapeo macro → categorías ETF (editable sin tocar código)
- [x] `data/etf_universe.yaml` — 32 ETFs PEA curados (Amundi + iShares)
- [x] `src/fetchers/` — news_fetcher, market_fetcher, geo_fetcher
- [x] `src/analysis/` — summarizer (Claude Call 1), signal_mapper, etf_ranker, recommender (Claude Call 2)
- [x] `src/delivery/` — email_delivery (Gmail + SendGrid), whatsapp_delivery (Twilio)
- [x] `src/scheduler.py` — APScheduler (daily/weekly/monthly)
- [x] `main.py` — CLI con `run-now`, `run-now --dry-run`, `schedule`
- [x] `deploy/financial-agent.service` — template systemd para Linux VPS
- [x] `venv/` creado localmente con todas las dependencias instaladas

### Lo que falta
- [ ] Crear el archivo `.env` con las claves (ver sección siguiente)
- [ ] Probar con `python main.py run-now --dry-run`
- [ ] Probar envío real con `python main.py run-now`
- [ ] (Opcional) Activar WhatsApp vía Twilio sandbox

---

## Próximo paso: crear el `.env`

Estás en la carpeta del proyecto. Crea el archivo `.env` (nunca se sube a git, está en `.gitignore`):

```bash
# En el terminal, desde agent_financial_advice/
copy .env.example .env
```

Luego edita `.env` con tus 5 datos:

```env
ANTHROPIC_API_KEY=sk-ant-...          # console.anthropic.com → API Keys
NEWSAPI_KEY=...                        # newsapi.org/account
GMAIL_USER=tu@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # App Password de Google (NO tu contraseña)
EMAIL_RECIPIENTS=tu@gmail.com
```

### Cómo obtener el Gmail App Password
1. Ve a **myaccount.google.com**
2. Seguridad → Verificación en 2 pasos → baja hasta **"Contraseñas de aplicaciones"**
3. Escribe un nombre (ej: `financial-agent`) → Crear
4. Google te da 16 caracteres — cópialos, no se vuelven a mostrar

---

## Cómo ejecutar

Siempre desde la carpeta `agent_financial_advice/`, usando el venv:

```bash
# Activar el entorno virtual (Windows)
venv\Scripts\activate

# Test sin enviar (ver el newsletter en consola)
python main.py run-now --dry-run

# Enviar newsletter real (una vez)
python main.py run-now

# Activar el scheduler (corre automáticamente según settings.yaml)
python main.py schedule
```

---

## Configuración rápida (`config/settings.yaml`)

```yaml
schedule:
  frequency: weekly      # daily | weekly | monthly
  time: "08:00"          # hora de envío
  day_of_week: monday    # (si frequency=weekly)
  timezone: "Europe/Paris"

analysis:
  language: fr           # fr | es | en
  top_etf_picks: 5       # cuántos ETFs recomendar
```

---

## Arquitectura del pipeline

```
[Datos — en paralelo]
  NewsAPI + RSS feeds  →  artículos con URLs
  yfinance             →  VIX, índices, precios ETF
  GDELT API            →  eventos geopolíticos
          ↓
[Claude Call 1 — summarizer.py]
  Extrae señales macro + URLs aprobadas (anti-alucinación)
          ↓
[signal_mapper.py — sin LLM]
  Señales → scores por categoría ETF (via signal_map.yaml)
          ↓
[etf_ranker.py — sin LLM]
  Rankea ETFs del universo → top N candidatos con performance
          ↓
[Claude Call 2 — recommender.py]
  Genera newsletter Markdown completo
          ↓
[Delivery]
  email_delivery.py    →  Markdown → HTML, envío Gmail/SendGrid
  whatsapp_delivery.py →  texto plano chunkeado, Twilio API
```

---

## Estructura de archivos clave

```
agent_financial_advice/
├── main.py                      ← punto de entrada (CLI)
├── .env                         ← TUS CLAVES (crear, no está en git)
├── .env.example                 ← template de referencia
├── config/
│   ├── settings.yaml            ← configuración principal
│   └── signal_map.yaml          ← mapeo señales → ETF categories
├── data/
│   └── etf_universe.yaml        ← los 32 ETFs del universo PEA
├── src/
│   ├── fetchers/                ← obtención de datos
│   ├── analysis/                ← pipeline de análisis + Claude
│   ├── delivery/                ← email + WhatsApp
│   └── utils/                   ← config, cache, logger
├── deploy/
│   └── financial-agent.service  ← para Linux VPS (systemd)
└── venv/                        ← entorno virtual Python (local)
```

---

## Para activar WhatsApp (opcional, más adelante)

1. Crear cuenta en **twilio.com** (gratis para sandbox)
2. Activar el sandbox de WhatsApp en Twilio Console
3. Añadir al `.env`:
   ```env
   TWILIO_ACCOUNT_SID=ACxxxxxxxx
   TWILIO_AUTH_TOKEN=...
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   WHATSAPP_RECIPIENTS=whatsapp:+33612345678
   ```
4. En `config/settings.yaml`, cambiar `whatsapp.enabled: true`

---

## Para desplegar en servidor Linux (más adelante)

```bash
# En el VPS:
git clone https://github.com/dav170699/tic-tac-toe.git
cd tic-tac-toe/agent_financial_advice
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env   # poner las claves

# Copiar el service de systemd:
sudo cp deploy/financial-agent.service /etc/systemd/system/
# Editar el .service para poner tu usuario y ruta correcta
sudo systemctl enable financial-agent
sudo systemctl start financial-agent
sudo journalctl -u financial-agent -f   # ver logs en vivo
```

---

## Costes estimados (newsletter semanal, uso personal)

| Servicio | Coste |
|---|---|
| Claude Sonnet (2 llamadas/semana) | ~$0.50–1.50/mes |
| NewsAPI.org | Gratis (100 req/día) |
| GDELT + yfinance + RSS | Gratis |
| Gmail SMTP | Gratis |
| Twilio WhatsApp (si activo) | ~$1–2/mes |
| **Total estimado** | **~$1.50–3.50/mes** |
