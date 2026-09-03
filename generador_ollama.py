import os
import sys
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

def extraer_texto(url):
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    texto = soup.get_text(separator="\n", strip=True)
    return "\n".join([l.strip() for l in texto.splitlines() if l.strip()])

def generar_articulo(contenido, url):
    # Fecha actual en ISO
    now = datetime.now().isoformat() + "Z"

    prompt = f"""
Eres un **copywriter experto y arquitecto de contenido**. Tu misión es transformar el siguiente contenido en un **artículo completo, profundo y bien estructurado** listo para publicar en un blog.

Reglas de Oro:
1. Investiga a fondo el tema.
2. No inventes información.
3. Estructura el contenido de forma lógica y profesional.
4. Genera un artículo largo (2500-3500 palabras).
5. Usa markdown limpio.
6. Solo incluye contenido relevante al tema.
7. Formato de salida: TODO dentro de una caja de código con triple backtick y el marcado `markdown`.

Estructura del Frontmatter (YAML):
---
title: '[Título atractivo y SEO, máximo 5-6 palabras]'
slug: [versión del título en minúsculas con guiones, máximo 3-4 palabras clave]
description: '[Meta descripción atractiva para SEO, máximo 160 caracteres]'
type: post
lang: es-ES
draft: false
authors:
  - Admin
pubDate: {now}
updatedDate: {now}
categories:
  - [elige UNA O MÚLTIPLES de: biodanza, tecnologia, cuatro-elementos, documentacion, literatura]
tags:
  - [3-8 tags relevantes en minúsculas]
featured: false
allowComments: false
share: true
image: '/img/[slug-del-post].webp'
imageAlt: '[Texto descriptivo SEO y accesible para la imagen]'
canonicalUrl: {url}
aliases:
  - '[Variación 1 del título]'
  - '[Variación 2 del título]'
  - '[Variación 3 del título]'
noIndex: false
showTOC: true
hideCoverImage: false
---

Luego, el cuerpo del artículo en Markdown con: introducción, desarrollo (4-5 subtemas), conclusión y referencias.

Contenido a procesar:
{contenido[:12000]}
"""
    # Llamar a Ollama directamente
    payload = {
        "model": "qwen2.5-coder:7b-64k",
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 65536,
            "temperature": 0.7,
            "top_p": 0.9
        }
    }
    resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()["response"]

def guardar_post(texto, url):
    # Extraer slug del frontmatter o generar uno
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

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        url = sys.argv[1]
    else:
        url = input("🔗 Introduce la URL a procesar: ").strip()
        if not url:
            print("❌ No se proporcionó URL.")
            sys.exit(1)

    print(f"🔍 Extrayendo contenido de: {url}")
    contenido = extraer_texto(url)
    if not contenido:
        print("❌ No se pudo extraer contenido.")
        sys.exit(1)

    print("📝 Generando artículo con Ollama... (puede tardar 2-4 min)")
    respuesta = generar_articulo(contenido, url)
    if not respuesta:
        print("❌ No se recibió respuesta.")
        sys.exit(1)

    # Extraer bloque de código markdown (si existe)
    bloque = re.search(r'```markdown\s*(.*?)\s*```', respuesta, re.DOTALL)
    if bloque:
        texto_post = bloque.group(1).strip()
    else:
        texto_post = respuesta

    guardar_post(texto_post, url)
