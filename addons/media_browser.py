import os
import re
import time
import json
import base64
import queue
import threading
import subprocess

os.environ.setdefault("QT_API", "pyside6")

import qtawesome as qta
from PySide6.QtCore import (
    Qt, QRectF, QSize, QObject, QThread, QTimer, Signal, Slot, QByteArray
)
from PySide6.QtGui import QPainter, QPainterPath, QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSlider,
    QSizePolicy,
)


BASE_DIR = os.path.join("files", "media_browser")
PS_SCRIPT_PATH = os.path.join(BASE_DIR, "media_session_worker.ps1")

#enserio espero que esto no sea un virus, que lo hizo claude y despues
#gemini arreglo bugs XDDDDD
#no entienod nada de power shell ajdfgsbgusbiug
#pero no parece tener nada raro


#igual bastante de este codigo si fue hecho muy como
#oye gemini ayudame con esto woo
#oye claude , enseñame que necesito, uuu
PS_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$OutputEncoding = [System.Text.Encoding]::UTF8

try {
    $rawui = $Host.UI.RawUI
    $tam = $rawui.BufferSize
    $tam.Width = 20000
    $rawui.BufferSize = $tam
} catch {}

function Write-Line([string]$Texto) {
    [Console]::Out.WriteLine($Texto)
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null

[void][Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStreamReference,Windows.Storage.Streams,ContentType=WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStreamWithContentType,Windows.Storage.Streams,ContentType=WindowsRuntime]

$AsTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await-Op($WinRtTask, [Type]$ResultType) {
    if ($null -eq $WinRtTask) { return $null }
    try {
        $m = $AsTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $m.Invoke($null, @($WinRtTask))
        if (-not $netTask.Wait(3000)) { return $null }
        return $netTask.Result
    } catch {
        return $null
    }
}

$AsTaskProgressGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperationWithProgress`2'
})[0]

function Await-OpProgress($WinRtTask, [Type]$ResultType, [Type]$ProgressType) {
    if ($null -eq $WinRtTask) { return $null }
    try {
        $m = $AsTaskProgressGeneric.MakeGenericMethod($ResultType, $ProgressType)
        $netTask = $m.Invoke($null, @($WinRtTask))
        if (-not $netTask.Wait(3000)) { return $null }
        return $netTask.Result
    } catch {
        return $null
    }
}

function Get-Manager {
    return Await-Op ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) `
        ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
}

function Get-MediaJson {
    try {
        $manager = Get-Manager
        if (-not $manager) { return '{"active":false}' }

        $session = $manager.GetCurrentSession()
        if (-not $session) { return '{"active":false}' }

        $props = Await-Op ($session.TryGetMediaPropertiesAsync()) `
            ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
        $playback = $session.GetPlaybackInfo()
        $timeline = $session.GetTimelineProperties()

        $thumb = ""
        $thumbDebug = "sin_metadata_de_carátula"
        if ($props -and $props.Thumbnail) {
            try {
                $stream = Await-Op ($props.Thumbnail.OpenReadAsync()) `
                    ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
                if ($stream) {
                    $metodoAsStream = [System.IO.WindowsRuntimeStreamExtensions].GetMethod(
                        'AsStreamForRead',
                        [System.Reflection.BindingFlags]'Public,Static',
                        $null,
                        [Type[]]@([Windows.Storage.Streams.IRandomAccessStream]),
                        $null
                    )
                    $netStream = $metodoAsStream.Invoke($null, @($stream))

                    if ($netStream) {
                        try {
                            $ms = New-Object System.IO.MemoryStream
                            try {
                                $netStream.CopyTo($ms)
                                if ($ms.Length -gt 0) {
                                    $thumb = [Convert]::ToBase64String($ms.ToArray())
                                    $thumbDebug = "ok"
                                } else {
                                    $thumbDebug = "stream_vacío_tras_CopyTo"
                                }
                            } finally {
                                try { $ms.Dispose() } catch {}
                            }
                        } finally {
                            try { $netStream.Dispose() } catch {}
                        }
                    } else {
                        $thumbDebug = "AsStreamForRead_devolvió_null"
                    }
                    try { $stream.Dispose() } catch {}
                } else {
                    $thumbDebug = "OpenReadAsync_devolvió_null"
                }
            } catch {
                $thumbDebug = "excepción: $($_.Exception.Message)"
            }
        }

        $status = "Unknown"
        if ($playback -and $playback.PlaybackStatus) { $status = $playback.PlaybackStatus.ToString() }

        $pos = 0
        $dur = 0
        if ($timeline) {
            try { $pos = [math]::Round($timeline.Position.TotalSeconds, 1) } catch {}
            try { $dur = [math]::Round($timeline.EndTime.TotalSeconds, 1) } catch {}
        }

        $tituloVal = "Sin titulo"
        if ($props -and $props.Title) { $tituloVal = $props.Title }
        $artistaVal = ""
        if ($props -and $props.Artist) { $artistaVal = $props.Artist }

        $obj = [PSCustomObject]@{
            active    = $true
            title     = $tituloVal
            artist    = $artistaVal
            app       = $session.SourceAppUserModelId
            status    = $status
            position  = $pos
            duration  = $dur
            thumbnail = $thumb
            thumbnail_debug = $thumbDebug
        }
        return ($obj | ConvertTo-Json -Compress -Depth 3)
    } catch {
        return '{"active":false}'
    }
}

function Invoke-Control($action, $arg) {
    try {
        $manager = Get-Manager
        if (-not $manager) { return }
        $session = $manager.GetCurrentSession()
        if (-not $session) { return }

        switch ($action) {
            "NEXT"   { $session.TrySkipNextAsync() | Out-Null }
            "PREV"   { $session.TrySkipPreviousAsync() | Out-Null }
            "TOGGLE" { $session.TryTogglePlayPauseAsync() | Out-Null }
            "PLAY"   { $session.TryPlayAsync() | Out-Null }
            "PAUSE"  { $session.TryPauseAsync() | Out-Null }
            "SEEK" {
                $ticks = [long]([double]$arg * 10000000)
                $session.TryChangePlaybackPositionAsync($ticks) | Out-Null
            }
        }
    } catch {}
}

while ($true) {
    $cmd = [Console]::In.ReadLine()
    if ($null -eq $cmd) { break }
    $cmd = $cmd.Trim()

    if ($cmd -eq "GET") {
        Write-Line (Get-MediaJson)
    }
    elseif ($cmd -match '^SEEK:(.+)$') {
        Invoke-Control "SEEK" $Matches[1]
        Write-Line '{"ok":true}'
    }
    elseif ($cmd -match '^(NEXT|PREV|TOGGLE|PLAY|PAUSE)$') {
        Invoke-Control $cmd $null
        Write-Line '{"ok":true}'
    }
    else {
        Write-Line '{"error":"unknown_command"}'
    }
    Write-Line "###END###"
}
"""


def _asegurar_script() -> str:
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    with open(PS_SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(PS_SCRIPT)
    return PS_SCRIPT_PATH


def imagen_desde_base64(b64_str: str):
    if not b64_str:
        return None
    try:
        raw = base64.b64decode(b64_str)
        img = QImage.fromData(QByteArray(raw))
        return img if not img.isNull() else None
    except Exception:
        return None


def nombre_app_amigable(app_id: str) -> str:
    if not app_id:
        return "Desconocido"
    nombre = app_id
    if "!" in nombre:
        nombre = nombre.split("!")[0]
    if "_" in nombre:
        nombre = nombre.split("_")[0]
    if "." in nombre:
        partes = nombre.split(".")
        nombre = partes[-1] if partes[-1] else partes[0]

    nombre = nombre.replace(".exe", "").replace(".EXE", "")

    alias = {
        "chrome": "Chrome",
        "msedge": "Edge",
        "firefox": "Firefox",
        "spotify": "Spotify",
        "zunemusic": "Música (Windows)",
        "zunevideo": "Películas y TV",
        "308046b0af4a39cb": "Firefox",
    }
    if nombre.lower() in alias:
        return alias[nombre.lower()]

    si_es_hex_crudo = bool(nombre) and len(nombre) <= 20 and all(
        c in "0123456789ABCDEFabcdef" for c in nombre
    )
    if si_es_hex_crudo:
        return ""

    return nombre if nombre else "Desconocido"


class MediaSessionWorker(QObject):
    datos_actualizados = Signal(dict)
    error_ocurrido = Signal(str)

    def __init__(self, intervalo_ms: int = 1500):
        super().__init__()
        self.intervalo_ms = intervalo_ms
        self.proceso = None
        self._cola_salida = None
        self._hilo_lector = None
        self._lock = threading.Lock()
        self.timer = None
    @Slot()
    def iniciar(self):
        self._lanzar_proceso()
        self.timer = QTimer()
        self.timer.setInterval(self.intervalo_ms)
        self.timer.timeout.connect(self._poll)
        self.timer.start()
        # primera lectura inmediata, sin esperar al primer tick
        QTimer.singleShot(50, self._poll)

    @Slot()
    def pausar(self):
        # Detiene el sondeo y mata el proceso de PowerShell mientras la
        # sección de Media no está visible, para no seguir gastando CPU/RAM
        # en un proceso que nadie está mirando.
        if self.timer:
            self.timer.stop()
        self._matar_proceso()

    @Slot()
    def reanudar(self):
        if not self._proceso_vivo():
            self._lanzar_proceso()
        if self.timer:
            self.timer.start()
            QTimer.singleShot(50, self._poll)

    def _lanzar_proceso(self):
        self._matar_proceso()
        script_path = _asegurar_script()
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW

            self.proceso = subprocess.Popen(
                [
                    "powershell.exe",
                    "-MTA",                    
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy", "Bypass",
                    "-File", script_path,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="ignore",
                bufsize=1,
                creationflags=creationflags,
            )
            self._cola_salida = queue.Queue()
            self._hilo_lector = threading.Thread(
                target=self._leer_salida, daemon=True
            )
            self._hilo_lector.start()
        except Exception as e:
            self.proceso = None
            self.error_ocurrido.emit(f"No se pudo iniciar PowerShell: {e}")

    def _leer_salida(self):
        proc = self.proceso
        if proc is None or proc.stdout is None:
            return
        try:
            for linea in iter(proc.stdout.readline, ""):
                self._cola_salida.put(linea.strip())
        except Exception:
            pass

    def _matar_proceso(self):
        if self.proceso is not None:
            try:
                if self.proceso.stdin:
                    self.proceso.stdin.close()
            except Exception:
                pass
            try:
                self.proceso.terminate()
            except Exception:
                pass
        self.proceso = None

    def _proceso_vivo(self) -> bool:
        return self.proceso is not None and self.proceso.poll() is None

    def _enviar_comando(self, comando: str, timeout: float = 3.0):
        if not self._proceso_vivo():
            self._lanzar_proceso()
            if not self._proceso_vivo():
                return None

        with self._lock:
            try:
                self.proceso.stdin.write(comando + "\n")
                self.proceso.stdin.flush()
            except Exception:
                self._lanzar_proceso()
                return None

            lineas = []
            fin = time.time() + timeout
            while time.time() < fin:
                restante = max(0.05, fin - time.time())
                try:
                    linea = self._cola_salida.get(timeout=restante)
                except queue.Empty:
                    break
                if linea == "###END###":
                    return "\n".join(lineas) if lineas else '{"active":false}'
                if linea:
                    lineas.append(linea)
            self._matar_proceso()
            return None

    @Slot()
    def _poll(self):
        respuesta = self._enviar_comando("GET")
        if respuesta is None:
            self.datos_actualizados.emit({"active": False})
            return
        try:
            data = json.loads(respuesta)
        except json.JSONDecodeError:
            data = {"active": False}
        self.datos_actualizados.emit(data)

    @Slot(str)
    def enviar_control(self, comando: str):
        self._enviar_comando(comando, timeout=2.0)
        QTimer.singleShot(250, self._poll)

    def detener(self):
        if self.timer:
            self.timer.stop()
        self._matar_proceso()



class MediaBrowserController(QObject):
    datos_actualizados = Signal(dict)
    _solicitar_control = Signal(str)
    _solicitar_pausa = Signal()
    _solicitar_reanudar = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hilo = QThread()
        self.worker = MediaSessionWorker(intervalo_ms=4000) 
        self.worker.moveToThread(self.hilo)

        self.hilo.started.connect(self.worker.iniciar)
        self.worker.datos_actualizados.connect(self.datos_actualizados)
        self._solicitar_control.connect(self.worker.enviar_control)
        self._solicitar_pausa.connect(self.worker.pausar)
        self._solicitar_reanudar.connect(self.worker.reanudar)

        self.hilo.start()

    def enviar_control(self, accion: str):
        self._solicitar_control.emit(accion)

    def pausar(self):
        self._solicitar_pausa.emit()

    def reanudar(self):
        self._solicitar_reanudar.emit()

    def siguiente(self):
        self.enviar_control("NEXT")

    def anterior(self):
        self.enviar_control("PREV")

    def alternar_reproduccion(self):
        self.enviar_control("TOGGLE")

    def buscar_posicion(self, segundos: float):
        self.enviar_control(f"SEEK:{segundos}")

    def detener(self):
        self.worker.detener()
        self.hilo.quit()
        self.hilo.wait(2000)


def redondear_pixmap(pixmap: QPixmap, radio: int) -> QPixmap:
    if pixmap.isNull():
        return pixmap

    tam = pixmap.size()
    resultado = QPixmap(tam)
    resultado.fill(Qt.transparent)

    painter = QPainter(resultado)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    ruta = QPainterPath()
    ruta.addRoundedRect(QRectF(0, 0, tam.width(), tam.height()), radio, radio)
    painter.setClipPath(ruta)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return resultado


def formatear_tiempo(segundos: float) -> str:
    segundos = max(0, int(segundos or 0))
    minutos, segs = divmod(segundos, 60)
    return f"{minutos}:{segs:02d}"


class MediaBrowserWidget(QWidget):
    TAMANO_CARATULA = 340
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._reproduciendo = False
        self._duracion_actual = 0
        self._usuario_arrastrando_slider = False

        self._construir_interfaz()

        self.controller = MediaBrowserController(parent=self)
        self.controller.datos_actualizados.connect(self._actualizar_ui)

        self._mostrar_estado_vacio()
        self._posicion_actual = 0
        self._titulo_actual = ""
        self.timer_progreso = QTimer(self)
        self.timer_progreso.setInterval(1000) 
        self.timer_progreso.timeout.connect(self._avanzar_progreso_local)
        self.timer_progreso.start()

    def showEvent(self, event):
        # Al volver a esta sección, reanudamos el sondeo y relanzamos el
        # proceso de PowerShell si fue detenido.
        if not self.timer_progreso.isActive():
            self.timer_progreso.start()
        self.controller.reanudar()
        super().showEvent(event)

    def hideEvent(self, event):
        # Al salir de la sección, pausamos el sondeo local y le pedimos al
        # worker que detenga el timer y mate el proceso powershell.exe, que
        # de otro modo quedaría corriendo en segundo plano indefinidamente
        # aunque nunca vuelvas a abrir esta pantalla.
        self.timer_progreso.stop()
        self.controller.pausar()
        super().hideEvent(event)

    def _construir_interfaz(self):
        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)

        self.tarjeta = QFrame()
        self.tarjeta.setObjectName("panelDerechoPlayer")
        self.tarjeta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout_tarjeta = QHBoxLayout(self.tarjeta)
        layout_tarjeta.setContentsMargins(48, 48, 48, 48)
        layout_tarjeta.setSpacing(48)

        self.lbl_caratula = QLabel()
        self.lbl_caratula.setObjectName("lblCaratulaPlayer")
        self.lbl_caratula.setFixedSize(self.TAMANO_CARATULA, self.TAMANO_CARATULA)
        self.lbl_caratula.setAlignment(Qt.AlignCenter)
        self.lbl_caratula.setScaledContents(False)
        self.lbl_caratula.setStyleSheet("border-radius: 12px;")
        fuente_glifo = self.lbl_caratula.font()
        fuente_glifo.setPointSize(int(self.TAMANO_CARATULA * 0.14))
        self.lbl_caratula.setFont(fuente_glifo)
        layout_tarjeta.addWidget(self.lbl_caratula, 0, Qt.AlignVCenter)

        columna_derecha = QVBoxLayout()
        columna_derecha.setSpacing(28)
        columna_derecha.addStretch()

        bloque_info = QVBoxLayout()
        bloque_info.setSpacing(10)

        self.lbl_titulo = QLabel("Nada reproduciéndose")
        self.lbl_titulo.setWordWrap(True)
        self.lbl_titulo.setStyleSheet("font-size: 30px; font-weight: bold;")

        fila_artista = QHBoxLayout()
        fila_artista.setSpacing(12)

        self.lbl_artista = QLabel("")
        self.lbl_artista.setObjectName("lblGenerosEstado")
        self.lbl_artista.setStyleSheet("font-size: 17px;")

        self.lbl_app = QLabel("")
        self.lbl_app.setObjectName("lblGenerosEstado")
        self.lbl_app.setStyleSheet("font-size: 13px; font-weight: bold;")

        fila_artista.addWidget(self.lbl_artista)
        fila_artista.addWidget(self.lbl_app)
        fila_artista.addStretch()

        bloque_info.addWidget(self.lbl_titulo)
        bloque_info.addLayout(fila_artista)

        columna_derecha.addLayout(bloque_info)
        fila_controles = QHBoxLayout()
        fila_controles.setSpacing(18)

        self.btn_anterior = self._crear_boton_control('fa5s.step-backward', 24)
        self.btn_play_pause = self._crear_boton_control('fa5s.play', 26, principal=True)
        self.btn_siguiente = self._crear_boton_control('fa5s.step-forward', 24)

        self.btn_anterior.clicked.connect(self._on_anterior)
        self.btn_play_pause.clicked.connect(self._on_play_pause)
        self.btn_siguiente.clicked.connect(self._on_siguiente)

        fila_controles.addWidget(self.btn_anterior)
        fila_controles.addWidget(self.btn_play_pause)
        fila_controles.addWidget(self.btn_siguiente)
        fila_controles.addStretch()

        columna_derecha.addLayout(fila_controles)

        self.fila_progreso = QWidget()
        layout_progreso = QHBoxLayout(self.fila_progreso)
        layout_progreso.setContentsMargins(0, 0, 0, 0)
        layout_progreso.setSpacing(14)

        self.lbl_tiempo_actual = QLabel("0:00")
        self.lbl_tiempo_actual.setStyleSheet("font-size: 13px;")

        self.slider_progreso = QSlider(Qt.Horizontal)
        self.slider_progreso.setRange(0, 0)
        self.slider_progreso.setFixedHeight(24)
        self.slider_progreso.sliderPressed.connect(self._on_slider_pressed)
        self.slider_progreso.sliderReleased.connect(self._on_slider_released)
        self._aplicar_estilo_slider()

        self.lbl_tiempo_total = QLabel("0:00")
        self.lbl_tiempo_total.setStyleSheet("font-size: 13px;")

        layout_progreso.addWidget(self.lbl_tiempo_actual)
        layout_progreso.addWidget(self.slider_progreso, 1)
        layout_progreso.addWidget(self.lbl_tiempo_total)

        columna_derecha.addWidget(self.fila_progreso)
        self.fila_progreso.hide()

        columna_derecha.addStretch()

        layout_tarjeta.addLayout(columna_derecha, 1)

        layout_raiz.addWidget(self.tarjeta)

    def _crear_boton_control(self, icono: str, tamano_icono: int, principal: bool = False) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("icono_qta", icono)
        btn.setIconSize(QSize(tamano_icono, tamano_icono))
        btn.setFixedSize(72, 72)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("border-radius: 16px;")
        if principal:
            btn.setCheckable(True)
            btn.setChecked(True)
        return btn

    def _color_icono(self, widget: QWidget) -> str:
        color = widget.palette().color(widget.foregroundRole())
        if color.isValid() and color != Qt.black:
            return color.name()
        return "#a6adc8"

    def _color_handle_slider(self) -> str:
        hoja = QApplication.instance().styleSheet() or ""
        m = re.search(
            r"QSlider::handle[^{]*\{[^}]*background\s*:\s*(#[0-9a-fA-F]{3,8})",
            hoja,
        )
        if m:
            return m.group(1)
        return "#a6adc8"

    def _aplicar_estilo_slider(self):
        color_acento = self._color_handle_slider()
        self.slider_progreso.setStyleSheet(f"""
            QSlider::sub-page:horizontal {{
                background: {color_acento};
                border-radius: 3px;
            }}
            QSlider::add-page:horizontal {{
                background: transparent;
            }}
        """)

    def _refrescar_iconos(self):
        self.btn_play_pause.setChecked(True)
        self.btn_anterior.setIcon(
            qta.icon(self.btn_anterior.property("icono_qta"), color=self._color_icono(self.btn_anterior))
        )
        self.btn_siguiente.setIcon(
            qta.icon(self.btn_siguiente.property("icono_qta"), color=self._color_icono(self.btn_siguiente))
        )
        icono_pp = 'fa5s.pause' if self._reproduciendo else 'fa5s.play'
        self.btn_play_pause.setIcon(qta.icon(icono_pp, color=self._color_icono(self.btn_play_pause)))

    def _mostrar_caratula_vacia(self):
        self.lbl_caratula.setPixmap(QPixmap())
        self.lbl_caratula.setText("▶")
        self.lbl_caratula.setFixedSize(self.TAMANO_CARATULA, self.TAMANO_CARATULA)

    def _mostrar_caratula(self, pixmap: QPixmap):
        self.lbl_caratula.setText("")
        
        pixmap_escalado = pixmap.scaled(
            self.TAMANO_CARATULA,
            self.TAMANO_CARATULA,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.lbl_caratula.setFixedSize(pixmap_escalado.size())
        self.lbl_caratula.setPixmap(redondear_pixmap(pixmap_escalado, 12))

    def _mostrar_estado_vacio(self):
        self.lbl_titulo.setText("Nada reproduciéndose")
        self.lbl_artista.setText("Reproduce algo en Spotify, tu navegador, etc.")
        self.lbl_app.hide()
        self._mostrar_caratula_vacia()
        self.fila_progreso.hide()
        self._reproduciendo = False
        self._refrescar_iconos()

    def _actualizar_ui(self, data: dict):
        if not data or not data.get("active"):
            self._mostrar_estado_vacio()
            return

        titulo = data.get("title") or "Sin título"
        artista = data.get("artist") or ""
        app_id = data.get("app") or ""
        estado = (data.get("status") or "").lower()
        
        posicion_ps = data.get("position") or 0
        duracion = data.get("duration") or 0
        thumb_b64 = data.get("thumbnail") or ""
        if titulo == self._titulo_actual:
            if posicion_ps < 1.5 and self._posicion_actual > 2:
                posicion_ps = self._posicion_actual
            if duracion == 0 and self._duracion_actual > 0:
                duracion = self._duracion_actual

        self._titulo_actual = titulo
        self._posicion_actual = posicion_ps
        self._duracion_actual = duracion

        self.lbl_titulo.setText(titulo)
        self.lbl_artista.setText(artista)

        nombre_app = nombre_app_amigable(app_id)
        if nombre_app:
            self.lbl_app.setText(f"· {nombre_app}")
            self.lbl_app.show()
        else:
            self.lbl_app.hide()

        imagen = imagen_desde_base64(thumb_b64)
        if imagen is not None:
            self._mostrar_caratula(QPixmap.fromImage(imagen))
        else:
            self._mostrar_caratula_vacia()

        self._reproduciendo = "playing" in estado
        self._refrescar_iconos()

        self.fila_progreso.show()

        if duracion > 0:
            self.slider_progreso.setEnabled(True)
            self.slider_progreso.setRange(0, int(duracion))
            
            if not self._usuario_arrastrando_slider:
                diferencia = abs(self.slider_progreso.value() - posicion_ps)
                if diferencia > 2 or self.slider_progreso.value() == 0:
                    self.slider_progreso.setValue(int(posicion_ps))
                    self.lbl_tiempo_actual.setText(formatear_tiempo(posicion_ps))
                    
            self.lbl_tiempo_total.setText(formatear_tiempo(duracion))
        else:
            self.slider_progreso.setEnabled(False)
            self.slider_progreso.setRange(0, 0)
            self.lbl_tiempo_actual.setText(formatear_tiempo(posicion_ps))
            self.lbl_tiempo_total.setText("0:00")

    def _on_anterior(self):
        self.controller.anterior()

    def _on_siguiente(self):
        self.controller.siguiente()

    def _on_play_pause(self):
        self._reproduciendo = not self._reproduciendo
        self._refrescar_iconos()
        self.controller.alternar_reproduccion()

    def _on_slider_pressed(self):
        self._usuario_arrastrando_slider = True

    def _on_slider_released(self):
        self._usuario_arrastrando_slider = False
        nueva_posicion = self.slider_progreso.value()
        self.controller.buscar_posicion(nueva_posicion)
    def closeEvent(self, event):
        self.controller.detener()
        super().closeEvent(event)

    def __del__(self):
        try:
            self.controller.detener()
        except Exception:
            pass


    def _avanzar_progreso_local(self):
        if self._reproduciendo and self._duracion_actual > 0 and not self._usuario_arrastrando_slider:
            self._posicion_actual += 1
            
            if self._posicion_actual > self._duracion_actual:
                self._posicion_actual = self._duracion_actual
                
            self.slider_progreso.setValue(int(self._posicion_actual))
            self.lbl_tiempo_actual.setText(formatear_tiempo(self._posicion_actual))

    def _on_slider_released(self):
        self._usuario_arrastrando_slider = False
        nueva_posicion = self.slider_progreso.value()
        
        self._posicion_actual = nueva_posicion 
        self.lbl_tiempo_actual.setText(formatear_tiempo(nueva_posicion))
        
        self.controller.buscar_posicion(nueva_posicion)

def cargar_addon():
    widget = MediaBrowserWidget()
    return "Media", widget
