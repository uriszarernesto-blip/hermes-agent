import os
import sys
import requests
import subprocess
from bs4 import BeautifulSoup

def extraer(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    s = BeautifulSoup(r.text, "html.parser")
    for x in s(["script", "style"]):
        x.decompose()
    return "\n".join([l.strip() for l in s.get_text().splitlines() if l.strip()])

def generar(url, texto):
    prompt = f"""Eres copywriter. Genera artículo en Markdown con frontmatter YAML (title, slug, description, categories, tags). Luego cuerpo con introducción, desarrollo, conclusión.

Contenido: {texto[:8000]}"""
    cmd = [
        "uv", "run", "hermes", "chat", "--cli",
        "--provider", "custom",
        "--model", "qwen2.5-coder:7b-64k"
    ]
    env = os.environ.copy()
    env["HERMES_LLM_BASE_URL"] = "http://localhost:11434/v1"
    env["HERMES_LLM_CONTEXT_WINDOW"] = "65536"
    p = subprocess.run(cmd, input=prompt, text=True, capture_output=True, env=env, timeout=180)
    return p.stdout

if __name__ == "__main__":
    url = input("URL: ").strip()
    print("Extrayendo...")
    texto = extraer(url)
    print("Generando...")
    res = generar(url, texto)
    slug = url.split("/")[-1] or "post"
    with open(f"{slug}.md", "w") as f:
        f.write(res)
    print(f"Guardado en {slug}.md")
