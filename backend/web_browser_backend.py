from os import path, walk, remove
from pathlib import Path
from dataclasses import dataclass

@dataclass
class web_container:
    url: str
    logo: str
    file_path: str

def create_new_page(url, logo):
    nombre = Path(logo).stem
    ruta_archivo = path.join("files", "web_pages", f"{nombre}.txt")
    
    with open(ruta_archivo, "w") as f:
        f.write(f"{url}\n{logo}")

def load_pages():
    base_dir = path.join("files", "web_pages")
    for ruta, _, files in walk(base_dir):
        for file in files:
            web = path.join(ruta, file)
            with open(web, "r") as we:
                url = we.readline().strip() 
                logo = we.readline().strip()
                yield web_container(url=url, logo=logo, file_path=web)

def delete_page(file_path):
    if path.exists(file_path):
        remove(file_path)