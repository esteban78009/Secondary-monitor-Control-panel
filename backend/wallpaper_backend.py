from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from json import dump, load
from pathlib import Path
from typing import Callable, Optional

import requests
from PIL import Image, ImageOps
from PySide6.QtCore import QSettings, QSize, Qt, QThread, Signal
from PySide6.QtGui import QGuiApplication, QImage, QImageReader, QScreen
from PySide6.QtWidgets import QApplication

try:
    import winreg
except ImportError:
    winreg = None


DEFAULT_URL_API_STEAM = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
CONFIG_FILENAME = "config.json"
MAIN_PY_FILENAME = "main.py"
STANDALONE_DIR_NAME = ".yasb_wallpaper_configurator"

ORG_NAME = "EstebanApps"
APP_NAME = "PanelDeControl"
CLAVE_TEMA = "tema/archivo_qss"
THEMES_DIR = Path(__file__).resolve().parent.parent.parent / "themes"

REGEX_RES = r"(\d{3,4})\s*[xX*]\s*(\d{3,4})"
REGEX_FORCE_VERTICAL = r"(?i)portrait|mobile|phone"
REGEX_FORCE_HORIZONTAL = r"(?i)ultrawide|landscape"
REGEX_IGNORE = r"(?i)wallpaper|scene|audio responsive|customizable|everyone"
FULL_FILE = "data_we_db.json"
CACHE_FILE = "db_we_not_processed.json"
COMBINED_WALLPAPER_FILENAME = "wallpaper_combinado.jpg"



def _default_config() -> dict:
    return {
        "STEAM_API_KEY": "",
        "URL_API_STEAM": DEFAULT_URL_API_STEAM,
        "we_exe": "",
        "we_content_folder": "",
        "monitors": [],
    }

def _default_monitor_entry(index: int) -> dict:
    return {
        "id": index,
        "we_monitor_id": str(index),
        "wallpaper_folder": "",
        "status_screen": "",
        "is_we": True,
        "we_project": "",
    }

class ProjectValidationError(Exception):
    """La carpeta seleccionada no parece ser un proyecto YASB válido."""

@dataclass
class ConfigManager:
    project_dir: Optional[str] = None
    standalone_dir: str = field(default_factory=lambda: os.path.join(
        os.path.expanduser("~"), STANDALONE_DIR_NAME
    ))
    data: dict = field(default_factory=_default_config)

    @property
    def is_linked(self) -> bool:
        return self.project_dir is not None

    @property
    def config_path(self) -> str:
        base = self.project_dir if self.is_linked else self.standalone_dir
        return os.path.join(base, CONFIG_FILENAME)

    @property
    def main_py_path(self) -> Optional[str]:
        if not self.is_linked:
            return None
        candidate = os.path.join(self.project_dir, MAIN_PY_FILENAME)
        return candidate if os.path.exists(candidate) else None

    @staticmethod
    def validate_project_dir(path: str) -> None:
        if not os.path.isdir(path):
            raise ProjectValidationError(f"La carpeta no existe: {path}")

        if not os.path.exists(os.path.join(path, MAIN_PY_FILENAME)):
            raise ProjectValidationError("No se encontró main.py en la carpeta seleccionada.")

        config_json = os.path.join(path, CONFIG_FILENAME)
        if not os.path.exists(config_json):
            raise ProjectValidationError("No se encontró config.json en la carpeta seleccionada.")

        try:
            with open(config_json, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            raise ProjectValidationError(f"config.json inválido: {exc}") from exc

        required_keys = {"we_exe", "we_content_folder", "monitors"}
        missing = required_keys - loaded.keys()
        if missing:
            raise ProjectValidationError(f"config.json no tiene el esquema esperado (faltan: {', '.join(missing)}).")

    def link_project(self, path: str) -> None:
        self.validate_project_dir(path)
        self.project_dir = os.path.abspath(path)
        self.load()

    def unlink_project(self) -> None:
        self.project_dir = None
        self.load()

    def load(self) -> dict:
        path = self.config_path
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            
            defaults = _default_config()
            for key, value in defaults.items():
                self.data.setdefault(key, value)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.data = _default_config()
            self.save()
        return self.data

    def save(self) -> None:
        path = self.config_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_monitor_entry(self, monitor_id: int) -> dict:
        monitors = self.data.setdefault("monitors", [])
        while len(monitors) <= monitor_id:
            monitors.append(_default_monitor_entry(len(monitors)))
        return monitors[monitor_id]

    def set_monitor_field(self, monitor_id: int, field_name: str, value) -> None:
        self.get_monitor_entry(monitor_id)[field_name] = value

    def sync_monitor_count(self, count: int) -> None:
        for i in range(count):
            self.get_monitor_entry(i)



@dataclass
class ImageWorker:
    qimage: QImage
    path: str
    func: Callable
    kind: str = "static"

class ImageLoader(QThread):
    image_loaded = Signal(object)
    end_reading = Signal()

    def __init__(self, folder_path: str, target: QSize, apply_func: Callable):
        super().__init__()
        self.folder_path = folder_path
        self.target = target
        self.extensions = (".png", ".jpg", ".jpeg")
        self.is_running = True
        self.apply_func = apply_func

    def run(self) -> None:
        if not self.folder_path or not os.path.isdir(self.folder_path):
            self.end_reading.emit()
            return

        with os.scandir(self.folder_path) as files:
            for file in files:
                if not self.is_running:
                    break
                if file.is_file() and file.name.lower().endswith(self.extensions):
                    reader = QImageReader(file.path)
                    q_image = reader.read()
                    if not q_image.isNull():
                        scaled = q_image.scaled(
                            self.target,
                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        x = (scaled.width() - self.target.width()) // 2
                        y = (scaled.height() - self.target.height()) // 2

                        final_image = scaled.copy(x, y, self.target.width(), self.target.height())
                        self.image_loaded.emit(
                            ImageWorker(final_image, file.path, self.apply_func, kind="static")
                        )
        self.end_reading.emit()

    def stop(self) -> None:
        self.is_running = False

class ImageLoader_WE(QThread):
    image_loaded = Signal(object)
    end_reading = Signal()

    def __init__(self, folder_path: str, target: QSize, orientation: str,
                 get_data_we: Callable[[str], dict], apply_func: Callable):
        super().__init__()
        self.folder_path = folder_path
        self.target = target
        self.orientation = orientation
        self.is_running = True
        self.get_data_we = get_data_we
        self.apply_func = apply_func

    def run(self) -> None:
        try:
            ids = self.get_data_we(self.folder_path)
            valid_ids = [
                wid for wid, info in ids.items()
                if isinstance(info, dict) and info.get("orientation", "both") in ("both", self.orientation)
            ]
        except Exception:
            self.end_reading.emit()
            return

        for wid in valid_ids:
            if not self.is_running:
                break

            item_folder = os.path.join(self.folder_path, str(wid))
            project_json_path = os.path.join(item_folder, "project.json")

            if not os.path.exists(project_json_path):
                continue

            try:
                with open(project_json_path, "r", encoding="utf-8") as f:
                    project_data = load(f)
            except Exception:
                continue

            img_path = os.path.join(item_folder, project_data.get("preview", ""))

            if not os.path.exists(img_path):
                continue

            try:
                pil_img = Image.open(img_path)

                if pil_img.format == "GIF":
                    pil_img.seek(0)

                pil_img = pil_img.convert("RGB")
                data_bytes = pil_img.tobytes("raw", "RGB")

                bytes_per_line = pil_img.width * 3
                q_image = QImage(data_bytes, pil_img.width, pil_img.height, bytes_per_line, QImage.Format.Format_RGB888)

                if not q_image.isNull():
                    scaled = q_image.scaled(
                        self.target,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    x = (scaled.width() - self.target.width()) // 2
                    y = (scaled.height() - self.target.height()) // 2

                    final_image = scaled.copy(x, y, self.target.width(), self.target.height())
                    self.image_loaded.emit(
                        ImageWorker(final_image, project_json_path, self.apply_func, kind="we")
                    )
            except Exception:
                pass

        self.end_reading.emit()

    def stop(self) -> None:
        self.is_running = False



@dataclass(frozen=True)
class MonitorInfo:
    index: int
    name: str
    x: int
    y: int
    width: int
    height: int
    is_primary: bool

    @property
    def orientation(self) -> str:
        return "vertical" if self.height > self.width else "horizontal"

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height else 1.0

def detect_monitors() -> list[MonitorInfo]:
    app = QGuiApplication.instance()
    if app is None:
        raise RuntimeError("Se necesita una QGuiApplication activa antes de detectar monitores.")

    primary: QScreen = app.primaryScreen()
    monitors: list[MonitorInfo] = []

    for i, screen in enumerate(app.screens()):
        geom = screen.geometry()
        monitors.append(
            MonitorInfo(
                index=i,
                name=screen.name() or f"Monitor {i}",
                x=geom.x(),
                y=geom.y(),
                width=geom.width(),
                height=geom.height(),
                is_primary=(screen is primary),
            )
        )
    return monitors

def virtual_desktop_bounds(monitors: list[MonitorInfo]) -> tuple[int, int, int, int]:
    min_x = min(m.x for m in monitors)
    min_y = min(m.y for m in monitors)
    max_x = max(m.x + m.width for m in monitors)
    max_y = max(m.y + m.height for m in monitors)
    return min_x, min_y, max_x, max_y

CLAVE_TEMA = "tema/archivo_qss"
CLAVE_CARPETA_TEMAS = "tema/carpeta_base" # NUEVA CLAVE
THEMES_DIR_DEFAULT = Path(__file__).resolve().parent.parent.parent / "themes"

def obtener_carpeta_temas() -> Path:
    settings = QSettings(ORG_NAME, APP_NAME)
    valor = settings.value(CLAVE_CARPETA_TEMAS, None)
    if valor:
        ruta = Path(valor)
        if ruta.exists():
            return ruta
    return THEMES_DIR_DEFAULT

def guardar_carpeta_temas(ruta: Path) -> None:
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(CLAVE_CARPETA_TEMAS, str(ruta))

def listar_temas() -> list[Path]:
    carpeta = obtener_carpeta_temas()
    if not carpeta.exists():
        return []
    return sorted(carpeta.glob("*.qss"))

def cargar_tema(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")

def aplicar_tema(ruta: Path) -> None:
    app = QApplication.instance()
    if app is None:
        return
    try:
        app.setStyleSheet(cargar_tema(ruta))
    except OSError:
        pass

def guardar_tema_preferido(ruta: Path) -> None:
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(CLAVE_TEMA, str(ruta))

def obtener_tema_guardado() -> Path | None:
    settings = QSettings(ORG_NAME, APP_NAME)
    valor = settings.value(CLAVE_TEMA, None)
    if valor:
        ruta = Path(valor)
        if ruta.exists():
            return ruta
    return None

def aplicar_tema_guardado_o_por_defecto() -> None:
    ruta = obtener_tema_guardado()
    if ruta is None:
        temas = listar_temas()
        if temas:
            ruta = temas[0]
    if ruta is not None:
        aplicar_tema(ruta)


class WallpaperEngineController:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def _work_dir(self) -> str:
        return os.path.dirname(self.config_manager.config_path)

    def _full_file_path(self) -> str:
        return os.path.join(self._work_dir(), FULL_FILE)

    def _cache_file_path(self) -> str:
        return os.path.join(self._work_dir(), CACHE_FILE)

    def get_data_we(self, we_content_folder: str) -> dict:
        if not we_content_folder or not os.path.isdir(we_content_folder):
            return {}

        ids = set(
            folder_id for folder_id in os.listdir(we_content_folder)
            if os.path.isdir(os.path.join(we_content_folder, folder_id)) and folder_id.isdigit()
        )

        full_file = self._full_file_path()
        res = {}
        if os.path.exists(full_file):
            try:
                with open(full_file, "r", encoding="utf-8") as f:
                    res = load(f)
            except Exception:
                pass

        rest_id = ids - set(res.keys())

        if rest_id:
            cache_file = self._cache_file_path()
            cache_data = {}
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache_data = load(f)
                except Exception:
                    pass

            news_id = self.download_classified(list(rest_id))
            cache_data.update(news_id["full"])
            res.update(news_id["classified"])

            with open(cache_file, "w", encoding="utf-8") as f:
                dump(cache_data, f, indent=4, ensure_ascii=False)

            with open(full_file, "w", encoding="utf-8") as f:
                dump(res, f, indent=4, ensure_ascii=False)

        return res

    def download_classified(self, ids_list: list[str]) -> dict:
        data = self.config_manager.data
        clave_api = data.get("STEAM_API_KEY", "")
        url_api = data.get("URL_API_STEAM", "")

        full_data: dict = {}
        classified_data: dict = {}

        for i in range(0, len(ids_list), 32):
            chunk = ids_list[i:i + 32]
            params = {"itemcount": len(chunk), "key": clave_api}

            for idx, wid in enumerate(chunk):
                params[f"publishedfileids[{idx}]"] = wid

            try:
                response = requests.post(url_api, data=params)
                response.raise_for_status()
                json_data = response.json()
            except Exception:
                continue

            items = json_data.get("response", {}).get("publishedfiledetails", [])

            for item in items:
                wid = item.get("publishedfileid")
                if not wid:
                    continue

                full_data[wid] = item
                raw_tags = item.get("tags") or []
                tags = " ".join(t.get("tag", "") for t in raw_tags if isinstance(t, dict))

                title = str(item.get("title") or "")
                desc = str(item.get("description") or "")

                context = f"{title} {tags} {desc}"
                clean_context = re.sub(REGEX_IGNORE, "", context)

                if re.search(REGEX_FORCE_VERTICAL, clean_context):
                    ori = "vertical"
                elif re.search(REGEX_FORCE_HORIZONTAL, clean_context):
                    ori = "horizontal"
                else:
                    match = re.search(REGEX_RES, context)
                    if match:
                        wide, largo = int(match.group(1)), int(match.group(2))
                        ori = "horizontal" if wide > largo else "vertical"
                    else:
                        ori = "both"

                classified_data[wid] = {"orientation": ori}

        return {"full": full_data, "classified": classified_data}

    def apply_wallpaper(self, image_path: str, monitor_id: int, screens) -> None:
        data = self.config_manager.data
        wallpaper_path = os.path.join(self._work_dir(), COMBINED_WALLPAPER_FILENAME)

        entry = self.config_manager.get_monitor_entry(monitor_id)
        entry["status_screen"] = image_path
        entry["is_we"] = False

        min_x = min(s.geometry().x() for s in screens)
        min_y = min(s.geometry().y() for s in screens)
        max_x = max(s.geometry().x() + s.geometry().width() for s in screens)
        max_y = max(s.geometry().y() + s.geometry().height() for s in screens)

        wide = max_x - min_x
        largo = max_y - min_y

        canvas = Image.new("RGB", (wide, largo), "black")

        for i, screen in enumerate(screens):
            geom = screen.geometry()
            res = (geom.width(), geom.height())

            try:
                img_path = self.config_manager.get_monitor_entry(i)["status_screen"]
                img = Image.open(img_path).convert("RGB")
                img = ImageOps.fit(img, res, method=Image.Resampling.LANCZOS)
            except Exception:
                img = Image.new("RGB", res, "black")

            x_rel = geom.x() - min_x
            y_rel = geom.y() - min_y
            canvas.paste(img, (x_rel, y_rel))

        canvas.save(wallpaper_path, "JPEG", quality=100)

        if hasattr(ctypes, "windll"):
            ctypes.windll.user32.SystemParametersInfoW(20, 0, wallpaper_path, 3)

        we_exe = data.get("we_exe", "")
        if we_exe:
            comando = f'"{we_exe}" -control closeWallpaper -monitor {monitor_id}'
            subprocess.Popen(comando, shell=True)

        self.config_manager.save()

    def apply_wallpaper_engine(self, project_path: str, monitor_id: int) -> None:
        data = self.config_manager.data
        we_exe = data.get("we_exe", "")
        if not we_exe:
            return

        entry = self.config_manager.get_monitor_entry(monitor_id)
        entry["is_we"] = True
        entry["we_project"] = project_path

        comando = f'"{we_exe}" -control openWallpaper -file "{project_path}" -monitor {monitor_id}'
        subprocess.Popen(comando, shell=True)

        self.config_manager.save()