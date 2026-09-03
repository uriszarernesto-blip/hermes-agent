#!/usr/bin/env python3
import os
import sys
import re
import requests
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

# Intentar importar trafilatura, si falla usar BeautifulSoup
try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

def extraer_texto(url):
    """Extrae texto limpio de una URL usando trafilatura o BeautifulSoup."""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, timeout=30, headers=headers)
    resp.raise_for_status()
    html = resp.text

    if trafilatura:
        texto = trafilatura.extract(html, include_comments=False, include_tables=False)
        if texto and len(texto) > 500:
            return texto

    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        texto = soup.get_text(separator="\n", strip=True)
        lineas = [l.strip() for l in texto.splitlines() if l.strip()]
        texto_limpio = "\n".join(lineas)
        if len(texto_limpio) > 500:
            return texto_limpio

    # Fallback: intentar con regex (menos fiable)
    texto = re.sub(r'<[^>]+>', ' ', html)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def generar_articulo(url, contenido):
    # Fecha actual en ISO (sin segundos ni microsegundos)
    fecha = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Prompt completo y directo (sin ambigüedades)
    prompt = f"""
Eres un copywriter experto. Debes generar un artículo en formato Markdown listo para publicar en un blog.

El artículo DEBE incluir:

1. Un frontmatter YAML con EXACTAMENTE esta estructura:
---
title: '[Título atractivo y SEO, máximo 5-6 palabras]'
slug: [versión del título en minúsculas con guiones, máximo 3-4 palabras]
description: '[Meta descripción atractiva, máximo 160 caracteres]'
type: post
lang: es-ES
draft: false
authors:
  - Admin
pubDate: {fecha}
updatedDate: {fecha}
categories:
  - [elige una de: biodanza, tecnologia, cuatro-elementos, documentacion, literatura]
tags:
  - [3-8 tags relevantes en minúsculas]
featured: false
allowComments: false
share: true
image: '/img/[slug-del-post].webp'
imageAlt: '[Texto descriptivo SEO]'
canonicalUrl: {url}
aliases:
  - '[Variación 1 del título]'
  - '[Variación 2 del título]'
  - '[Variación 3 del título]'
noIndex: false
showTOC: true
hideCoverImage: false
---

2. Luego, el cuerpo del artículo en Markdown con:
   - Un resumen introductorio (1-2 frases).
   - Un índice con enlaces a las secciones.
   - Una introducción (4-5 párrafos).
   - Desarrollo con 4-5 subtemas (cada uno con 4-5 párrafos).
   - Una conclusión (3-4 párrafos).
   - Referencias (bibliografía, fuentes web, videos, personas clave, organizaciones).

El artículo debe ser profundo, de 2500-3500 palabras, y usar un estilo profesional y atractivo.

Contenido a procesar (extraído de la URL):

{contenido[:12000]}

IMPORTANTE: Devuelve TODO el contenido dentro de una única caja de código con triple backtick y el marcado `markdown`. No escribas nada fuera de la caja de código. No incluyas saludos, explicaciones ni despedidas.
"""
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

def guardar_articulo(texto, url):
    # Buscar slug en el frontmatter
    match = re.search(r'slug:\s*([^\s]+)', texto)
    if match:
        slug = match.group(1).strip()
    else:
        # Generar slug desde el dominio
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
        print("❌ No se pudo extraer contenido de la URL. Verifica que la URL sea accesible y contenga texto.")
        sys.exit(1)

    # Mostrar los primeros 200 caracteres para diagnóstico
    print(f"📄 Contenido extraído (primeros 200 caracteres):\n{contenido[:200]}...\n")

    if len(contenido) < 500:
        print("⚠️ El contenido extraído es muy corto (menos de 500 caracteres). Puede que la URL no tenga texto suficiente.")
        continuar = input("¿Quieres continuar de todas formas? (s/n): ").strip().lower()
        if continuar != 's':
            sys.exit(1)

    print("📝 Generando artículo con Ollama... (puede tardar 2-4 minutos)")
    respuesta = generar_articulo(url, contenido)
    if not respuesta:
        print("❌ No se recibió respuesta del modelo.")
        sys.exit(1)

    # Extraer el bloque de código markdown
    bloque = re.search(r'```markdown\s*(.*?)\s*```', respuesta, re.DOTALL)
    if bloque:
        texto_post = bloque.group(1).strip()
    else:
        # Si no encuentra el bloque, usar toda la respuesta
        texto_post = respuesta

    guardar_articulo(texto_post, url)
