import os
import json
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QImage
from tinytag import TinyTag

BASE_DIR = os.path.join("files", "music_manager")
PLAYLIST = os.path.join(BASE_DIR, "PLAYLIST") 
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

EXTENSIONES = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')

TAMANO_MAX_CARATULA = 300

@dataclass
class data_music:
    titulo: str
    artista: str
    duracion: tuple
    imagen: QImage
    musica: str
    genero: str

def asegurar_carpeta(ruta: str):
    if not os.path.exists(ruta):
        os.makedirs(ruta)

def load_music(ruta: str):
    for path, _, files in os.walk(ruta):
        for file in files:
            if file.lower().endswith(EXTENSIONES):
                try:
                    ruta_completa = os.path.join(path, file)
                    tag = TinyTag.get(ruta_completa, image=True)
                    
                    titulo = os.path.splitext(file)[0]
                    artista = tag.artist or "artista desconocido"
                    genero = tag.genre or "Desconocido"
                    
                    duracion = tag.duration
                    duracion_tupla = (0, 0) if duracion is None else (int(duracion // 60), int(duracion % 60))
                    
                    data_imagen = tag.get_image()
                    imagen = None
                    if data_imagen:
                        imagen_cruda = QImage.fromData(data_imagen)
                        if not imagen_cruda.isNull():
                            imagen = imagen_cruda.scaled(
                                TAMANO_MAX_CARATULA,
                                TAMANO_MAX_CARATULA,
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation,
                            )
                    
                    yield data_music(
                        titulo=titulo,
                        artista=artista,
                        duracion=duracion_tupla,
                        musica=ruta_completa,
                        imagen=imagen,
                        genero=genero
                    )
                except Exception as e:
                    print(f"Error en {file}, {e}")

class EscaneoMusica(QThread):
    cancion = Signal(object)
    
    def __init__(self, ruta: str):
        super().__init__()
        self.ruta = ruta
    
    def run(self):
        try:
            for song in load_music(self.ruta):
                self.cancion.emit(song)
        except Exception as e:
            print(f"Ocurrió un error de tipo: {e}")

def cargar_configuracion() -> str:
    asegurar_carpeta(BASE_DIR)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("ruta_musica", "")
    return ""

def guardar_configuracion(ruta: str):
    asegurar_carpeta(BASE_DIR)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"ruta_musica": ruta}, f, indent=4, ensure_ascii=False)

def obtener_nombres_playlists() -> list:
    asegurar_carpeta(PLAYLIST)
    return [
        os.path.splitext(file)[0] 
        for file in os.listdir(PLAYLIST) 
        if file.endswith(".json")
    ]
    
def cargar_playlist(nombre: str) -> list:
    asegurar_carpeta(PLAYLIST)
    file_path = os.path.join(PLAYLIST, f"{nombre}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f).get("canciones", [])
    return []

def guardar_playlist(nombre: str, ruta: list):
    asegurar_carpeta(PLAYLIST)
    file_path = os.path.join(PLAYLIST, f"{nombre}.json")
    data = {
        "nombre": nombre,
        "canciones": ruta
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def eliminar_playlist(nombre: str):
    asegurar_carpeta(PLAYLIST)
    file_path = os.path.join(PLAYLIST, f"{nombre}.json")
    if os.path.exists(file_path):
        os.remove(file_path)





