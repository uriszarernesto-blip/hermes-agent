---
sidebar_position: 12
title: "Enviar la salida de un script a plataformas de mensajería"
description: "Utiliza `hermes send` para enviar texto de cualquier script de shell, tarea cron, hook de CI o demonio de monitoreo a Telegram, Discord, Slack, Signal y más."
---

# Enviar la salida de un script a plataformas de mensajería

`hermes send` es una CLI ligera y programable que permite enviar mensajes a cualquier plataforma de mensajería configurada en Hermes. Piensa en ella como un `curl` especializado en notificaciones multiplataforma: funciona sin necesidad de un gateway activo, sin LLM y sin tener que pegar tokens de bots repetidamente en cada script.

Casos de uso comunes:

- **Monitoreo del sistema:** Memoria, disco, temperatura de GPU o notificaciones de finalización de tareas largas.
- **Notificaciones de CI/CD:** Despliegues completados o pruebas fallidas.
- **Scripts de cron:** Tareas programadas que necesitan enviarte sus resultados.
- **Mensajes rápidos:** Envío de texto bajo demanda directamente desde la terminal.
- **Redirección de tuberías:** Canalizar la salida de cualquier herramienta (`make | hermes send --to slack:#builds`).

Este comando reutiliza las credenciales y los adaptadores de plataforma ya existentes en `hermes gateway`, evitando la necesidad de mantener un segundo conjunto de configuraciones.

---

## Inicio rápido

```bash
# Enviar texto plano al canal predeterminado de una plataforma
hermes send --to telegram "deploy finished"

# Redirigir el stdout de cualquier comando mediante tuberías (pipe)
echo "RAM 92%" | hermes send --to telegram:-1001234567890

# Enviar un archivo
hermes send --to discord:#ops --file /tmp/report.md

# Adjuntar una línea de asunto o título
hermes send --to slack:#eng --subject "[CI] build.log" --file build.log

# Especificar un hilo de destino (hilos de Discord, temas de foros en Telegram)
hermes send --to telegram:-1001234567890:17585 "threaded reply"

# Listar todos los destinos configurados
hermes send --list

# Filtrar destinos por plataforma
hermes send --list telegram

```

---

## Referencia de parámetros

| Flag | Descripción |
| --- | --- |
| `-t, --to TARGET` | Dirección de destino. Consulta [Formatos de destino](https://www.google.com/search?q=%23formatos-de-destino). |
| `message` *(posicional)* | Texto del mensaje. Se omite si se lee desde `--file` o stdin. |
| `-f, --file PATH` | Lee el cuerpo del mensaje desde un archivo. Usa `--file -` para forzar la lectura desde stdin. |
| `-s, --subject LINE` | Añade una línea de título o asunto antes del cuerpo del mensaje. |
| `-l, --list` | Lista los destinos disponibles. Parámetro posicional opcional para filtrar por plataforma. |
| `-q, --quiet` | No muestra salida en stdout si la operación es exitosa (solo retorna el código de salida, ideal para scripts). |
| `--json` | Muestra el resultado del envío en formato JSON plano. |
| `-h, --help` | Muestra el texto de ayuda integrado. |

### Formatos de destino {#formatos-de-destino}

| Formato | Ejemplo | Significado |
| --- | --- | --- |
| `platform` | `telegram` | Envía al canal predeterminado configurado para esa plataforma. |
| `platform:chat_id` | `telegram:-1001234567890` | Especifica un chat numérico, grupo o ID de usuario. |
| `platform:chat_id:thread_id` | `telegram:-1001234567890:17585` | Especifica un hilo o un tema de foro en Telegram. |
| `platform:#channel` | `discord:#ops` | Nombre de canal legible (resuelto mediante el directorio de canales). |
| `platform:+E164` | `signal:+15551234567` | Plataformas direccionadas por número telefónico (Signal, SMS, WhatsApp). |

Todas las plataformas que cuentan con un adaptador en Hermes pueden usarse como destino:
`telegram`, `discord`, `slack`, `signal`, `sms`, `whatsapp`, `matrix`,
`mattermost`, `feishu`, `dingtalk`, `wecom`, `weixin`, `email`, etc.

### Códigos de salida

| Código | Significado |
| --- | --- |
| `0` | Envío (o listado) exitoso. |
| `1` | Fallo de entrega a nivel de plataforma (autenticación, permisos, red). |
| `2` | Error de uso, parámetros o configuración. |

Los códigos de salida siguen las convenciones estándar de Unix, lo que permite a los scripts evaluar el resultado de la misma manera que lo harían con `curl` o `grep`.

---

## Orden de resolución del cuerpo del mensaje

`hermes send` resuelve el cuerpo del mensaje utilizando el siguiente orden de prioridad:

1. **Argumento posicional** — `hermes send --to telegram "hi"`
2. **Flag `--file PATH**` — `hermes send --to telegram --file msg.txt`
3. **Entrada estándar (stdin) por tubería** — `echo hi | hermes send --to telegram`

Cuando stdin es una TTY (sin tubería), Hermes **no** esperará ninguna entrada; en su lugar, devolverá un error de uso explícito. Esto evita que los scripts se queden colgados indefinidamente si se omite accidentalmente el cuerpo del mensaje.

---

## Ejemplos de uso real

### Monitoreo: Alertas de memoria y disco

Reemplaza las llamadas complejas a `curl https://api.telegram.org/...` en tus scripts de watchdog con una sola línea concisa:

```bash
#!/usr/bin/env bash
ram_pct=$(free | awk '/^Mem:/ {printf "%d", $3 * 100 / $2}')
if [ "$ram_pct" -ge 85 ]; then
  hermes send --to telegram --subject "⚠ MEMORY WARNING" \
    "RAM ${ram_pct}% on $(hostname)"
fi

```

Dado que `hermes send` reutiliza tu configuración global de Hermes, el mismo script puede ejecutarse en cualquier host que tenga instalado Hermes, sin necesidad de exportar manualmente tokens de bots a las variables de entorno de cada máquina.

:::tip No utilices el gateway para monitorearse a sí mismo
Para watchdogs críticos que deban activarse en caso de que el propio gateway falle (alertas de OOM, alertas de disco lleno), continúa utilizando llamadas directas con `curl` en lugar de `hermes send`. Si el intérprete de Python no puede cargarse debido a la inestabilidad de la máquina, aun así querrás que la alerta se envíe.
:::

### CI / CD: Resultados de compilación y pruebas

```bash
# En .github/workflows/deploy.yml o cualquier script de CI
if ./scripts/deploy.sh; then
  hermes send --to slack:#deploys "✅ ${CI_COMMIT_SHA:0:7} deployed"
else
  tail -n 100 deploy.log | hermes send \
    --to slack:#deploys --subject "❌ deploy failed"
  exit 1
fi

```

### Cron: Reportes diarios

```bash
# Entrada de Crontab
0 9 * * * /usr/local/bin/generate-metrics.sh \
  | /home/me/.hermes/bin/hermes send \
      --to telegram --subject "Daily metrics $(date +%Y-%m-%d)"

```

### Tareas largas: Notificación al finalizar

```bash
./train.py --epochs 200 && \
  hermes send --to telegram "training done" || \
  hermes send --to telegram "training failed (exit $?)"

```

### Uso de `--json` y `--quiet` en scripts

```bash
# Hace que el script falle si la entrega no es exitosa; no ensucia los logs si funciona
hermes send --to telegram --quiet "keepalive" || {
  echo "Telegram delivery failed" >&2
  exit 1
}

# Captura el ID del mensaje para editarlo o responder en el mismo hilo posteriormente
msg_id=$(hermes send --to discord:#ops --json "build started" \
  | jq -r .message_id)

```

---

## ¿Requiere `hermes send` que el gateway esté activo?

**Normalmente no.** Para todas las plataformas basadas en tokens de bots (Telegram, Discord, Slack, Signal, SMS, WhatsApp Cloud API, etc.), `hermes send` interactúa directamente con la interfaz REST de la plataforma utilizando las credenciales almacenadas en `~/.hermes/.env` y `~/.hermes/config.yaml`. Se ejecuta como un subproceso independiente y finaliza inmediatamente tras la entrega del mensaje.

El gateway en ejecución solo es necesario para aquellas **plataformas basadas en plugins** que requieren conexiones persistentes mediante adaptadores (por ejemplo, un plugin personalizado que mantiene una conexión WebSocket activa). En ese caso, recibirás un mensaje de error claro indicándote que inicies el gateway; ejecuta `hermes gateway start` e inténtalo de nuevo.

---

## Listar y descubrir destinos

Antes de enviar mensajes a un canal específico, puedes verificar los destinos disponibles:

```bash
# Listar todos los destinos de todas las plataformas configuradas
hermes send --list

# Listar únicamente los destinos de Telegram
hermes send --list telegram

# Formato legible por máquinas
hermes send --list --json

```

Los datos de la lista provienen de `~/.hermes/channel_directory.json`, el cual se actualiza automáticamente cada pocos minutos mientras el gateway está en ejecución. Si visualizas el mensaje "Aún no se han descubierto canales", inicia el gateway una vez (`hermes gateway start`) para poblar la caché.

Los nombres legibles (`discord:#ops`, `slack:#engineering`) se resuelven a través de esta caché en el momento del envío, eliminando la necesidad de memorizar IDs numéricos.

---

## Comparativa con otras soluciones

| Solución | Multiplataforma | Reutiliza credenciales Hermes | Requiere gateway | Ideal para |
| --- | --- | --- | --- | --- |
| `hermes send` | ✅ | ✅ | No (token de bot) | Todos los escenarios detallados abajo |
| `curl` directo por plataforma | Requiere desarrollo individual | Gestión manual | No | Watchdogs críticos |
| Tareas de `cron` con `--deliver` | ✅ | ✅ | No | Tareas programadas de agentes |
| Herramienta agente `send_message` | ✅ | ✅ | No | Dentro del bucle de ejecución del agente |

`hermes send` mantiene intencionalmente una interfaz minimalista. Si necesitas que un agente determine el contenido del mensaje, utiliza la herramienta `send_message` dentro de un chat o de una tarea cron. Si necesitas programar ejecuciones regulares y generar contenido mediante LLM, utiliza `cronjob(action='create', prompt=...)` con `deliver='telegram:...'`. Si solo necesitas redirigir cadenas de texto planas, utiliza directamente `hermes send`.

---

## Documentación relacionada

* [Automatizar todo con Cron](https://www.google.com/search?q=/guides/automate-with-cron) — Tareas programadas cuya salida se entrega automáticamente a cualquier plataforma.
* [Funcionamiento interno del Gateway](https://www.google.com/search?q=/developer-guide/gateway-internals) — El enrutador de entrega compartido por `hermes send` y las entregas de tareas cron.
* [Configuración de plataformas de mensajería](https://www.google.com/search?q=/user-guide/messaging/) — Instrucciones de configuración inicial para cada plataforma.