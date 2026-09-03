#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import requests
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def extraer_contenido(url):
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        texto = soup.get_text(separator="\n", strip=True)
        lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
        return "\n".join(lineas)
    except Exception as e:
        print(f"Error al extraer: {e}", file=sys.stderr)
        return None

def generar_post(url, contenido):
    reglas = """
Eres un copywriter experto y arquitecto de contenido. Tu misión es recibir contenido y transformarlo en un artículo completo, profundo y bien estructurado.

Reglas de Oro:
1. Investiga a fondo el tema.
2. No inventes información.
3. Estructura el contenido de forma lógica y profesional.
4. Genera un artículo largo (2500-3500 palabras).
5. Usa markdown limpio.
6. Solo incluye contenido relevante al tema.
7. Formato de salida: todo dentro de una caja de código con triple backtick y el marcado `markdown`.

Estructura del Frontmatter (YAML):
---
title: '[Título atractivo y SEO, máximo 5-6 palabras]'
slug: [versión del título en minúsculas con guiones, máximo 3-4 palabras clave]
description: '[Meta descripción atractiva, máximo 160 caracteres]'
type: post
lang: es-ES
draft: false
authors:
  - Admin
pubDate: [FECHA ACTUAL en formato ISO]
updatedDate: [MISMA FECHA]
categories:
  - [elige UNA O MÚLTIPLES de: biodanza, tecnologia, cuatro-elementos, documentacion, literatura]
tags:
  - [3-8 tags relevantes en minúsculas]
featured: false
allowComments: false
share: true
image: '/img/[slug-del-post].webp'
imageAlt: '[Texto descriptivo SEO]'
canonicalUrl: [USA EL ENLACE EXACTO si es URL, si no https://markeup.pages.dev/]
aliases:
  - '[Variación 1 del título]'
  - '[Variación 2 del título]'
  - '[Variación 3 del título]'
noIndex: false
showTOC: true
hideCoverImage: false
---

Luego el cuerpo del artículo en Markdown (introducción, desarrollo, conclusión, referencias).

Contenido proporcionado:
{sitio}
"""
    prompt = reglas.format(sitio=contenido)

    env = os.environ.copy()
    env.update({
        "HERMES_LLM_PROVIDER": "custom",
        "HERMES_LLM_MODEL": "qwen2.5-coder:7b-64k",
        "HERMES_LLM_BASE_URL": "http://localhost:11434/v1",
        "HERMES_LLM_CONTEXT_WINDOW": "65536"
    })

    cmd = ["uv", "run", "hermes", "chat", "--cli", "--verbose"]
    try:
        proceso = subprocess.run(cmd, input=prompt, text=True, capture_output=True, env=env, timeout=300)
        if proceso.returncode != 0:
            print("Error:", proceso.stderr, file=sys.stderr)
            return None
        return proceso.stdout
    except subprocess.TimeoutExpired:
        print("Tiempo de espera agotado.", file=sys.stderr)
        return None

def guardar_post(texto, url):
    match = re.search(r'slug:\s*([^\s]+)', texto)
    if match:
        slug = match.group(1).strip()
    else:
        slug = urlparse(url).netloc.replace('.', '-')
    if not slug.endswith('.md'):
        slug += '.md'
    ruta = Path(slug)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(texto)
    print(f"✅ Artículo guardado en: {ruta.resolve()}")
    return ruta

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        url = sys.argv[1]
    else:
        url = input("🔗 Introduce la URL a procesar: ").strip()
        if not url:
            print("❌ No se proporcionó ninguna URL.")
            sys.exit(1)

    print(f"🔍 Extrayendo contenido de: {url}")
    contenido = extraer_contenido(url)
    if not contenido:
        print("❌ No se pudo extraer contenido.")
        sys.exit(1)

    print("📝 Generando artículo... (puede tardar 2-4 minutos)")
    respuesta = generar_post(url, contenido)
    if not respuesta:
        print("❌ El agente no generó respuesta.")
        sys.exit(1)

    bloque = re.search(r'```markdown\s*(.*?)\s*```', respuesta, re.DOTALL)
    if bloque:
        texto_post = bloque.group(1).strip()
    else:
        texto_post = respuesta

    guardar_post(texto_post, url)
