import os
import json

# Forzar a qtawesome/qtpy a usar PySide6
os.environ["QT_API"] = "pyside6"
import qtawesome as qta

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFileDialog, QComboBox, QLineEdit, QFrame, QMessageBox, QGridLayout,
    QApplication
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

DIRECTORIO_POMODORO = os.path.join("files", "pomodoro")
ARCHIVO_PERFILES = os.path.join(DIRECTORIO_POMODORO, "perfiles.json")

class NumberPicker(QWidget):
    valueChanged = Signal(int)

    def __init__(self, titulo, min_v, max_v, default, icono_str=None):
        super().__init__()
        self.min_v = min_v
        self.max_v = max_v
        self.valor = default

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        if icono_str:
            lbl_icon = QLabel()
            lbl_icon.setObjectName("lblIconoPicker")
            lbl_icon.setPixmap(qta.icon(icono_str).pixmap(16, 16))
            header_layout.addWidget(lbl_icon)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("lblTituloPicker")
        lbl_titulo.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        header_layout.addWidget(lbl_titulo)
        header_layout.addStretch()

        fila_controles = QHBoxLayout()
        fila_controles.setSpacing(0)

        self.btn_menos = QPushButton("−")
        self.btn_menos.setObjectName("btnPickerMenos")
        self.lbl_num = QLabel(str(default))
        self.lbl_num.setObjectName("lblPickerNum")
        self.btn_mas = QPushButton("＋")
        self.btn_mas.setObjectName("btnPickerMas")
        self.btn_menos.setAutoRepeat(True)
        self.btn_menos.setAutoRepeatDelay(400)
        self.btn_menos.setAutoRepeatInterval(50)
        
        self.btn_mas.setAutoRepeat(True)
        self.btn_mas.setAutoRepeatDelay(400)
        self.btn_mas.setAutoRepeatInterval(50)

        estilo_btn = "font-size: 20px; font-weight: bold; padding: 8px;"
        self.btn_menos.setStyleSheet(estilo_btn + "border-top-left-radius: 8px; border-bottom-left-radius: 8px;")
        self.btn_mas.setStyleSheet(estilo_btn + "border-top-right-radius: 8px; border-bottom-right-radius: 8px;")
        
        self.lbl_num.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.lbl_num.setAlignment(Qt.AlignCenter)
        self.lbl_num.setMinimumWidth(50)

        self.btn_menos.clicked.connect(self.restar)
        self.btn_mas.clicked.connect(self.sumar)

        fila_controles.addWidget(self.btn_menos)
        fila_controles.addWidget(self.lbl_num)
        fila_controles.addWidget(self.btn_mas)

        layout.addLayout(header_layout)
        layout.addLayout(fila_controles)

    def restar(self):
        if self.valor > self.min_v:
            self.valor -= 1
            self.lbl_num.setText(str(self.valor))
            self.valueChanged.emit(self.valor)

    def sumar(self):
        if self.valor < self.max_v:
            self.valor += 1
            self.lbl_num.setText(str(self.valor))
            self.valueChanged.emit(self.valor)

    def value(self): 
        return self.valor
    
    def setValue(self, v):
        self.valor = v
        self.lbl_num.setText(str(v))


class PomodoroApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("pomodoroAppWindow")
        
        self.tiempo_restante = 25 * 60
        self.fase_actual = "Trabajo"
        self.sesion_actual = 1
        self.ruta_alarma = ""
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick_temporizador)
        
        self.timer_alarma = QTimer(self)
        self.timer_alarma.setSingleShot(True)
        self.timer_alarma.timeout.connect(self._detener_alarma)

        self._asegurar_directorios()
        self._construir_interfaz()
        self._cargar_perfiles()
        self._aplicar_configuracion_actual()

    def _asegurar_directorios(self):
        if not os.path.exists(DIRECTORIO_POMODORO):
            os.makedirs(DIRECTORIO_POMODORO)
        if not os.path.exists(ARCHIVO_PERFILES):
            datos = {
                "Defecto": {
                    "trabajo": 25, "descanso_corto": 5, "descanso_largo": 15, 
                    "sesiones": 4, "alarma": ""
                }
            }
            with open(ARCHIVO_PERFILES, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4)

    def _construir_interfaz(self):
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(30)
        panel_izquierdo = QFrame()
        panel_izquierdo.setObjectName("panelIzquierdoPomodoro")
        panel_izquierdo.setStyleSheet("border-radius: 20px;")
        
        layout_reloj = QVBoxLayout(panel_izquierdo)
        layout_reloj.setContentsMargins(30, 40, 30, 40)
        
        self.lbl_fase = QLabel(f"{self.fase_actual} · Sesión {self.sesion_actual}")
        self.lbl_fase.setObjectName("lblFasePomodoro")
        self.lbl_fase.setAlignment(Qt.AlignCenter)
        self.lbl_fase.setStyleSheet("font-size: 22px; font-weight: bold; border: none; letter-spacing: 2px;")
        
        self.lbl_tiempo = QLabel("25:00")
        self.lbl_tiempo.setObjectName("lblTiempoPomodoro")
        self.lbl_tiempo.setAlignment(Qt.AlignCenter)
        self.lbl_tiempo.setFont(QFont("Consolas", 85, QFont.Bold))
        self.lbl_tiempo.setStyleSheet("border: none; margin-top: 10px; margin-bottom: 20px;")
        
        layout_controles = QHBoxLayout()
        estilo_btn_accion = "font-size: 16px; font-weight: bold; padding: 12px; border-radius: 12px; border: none;"
        
        self.btn_iniciar = QPushButton(" INICIAR")
        self.btn_iniciar.setIcon(qta.icon('fa5s.play'))
        self.btn_iniciar.setObjectName("btnIniciarPomodoro")
        self.btn_iniciar.setProperty("estado", "detenido")
        self.btn_iniciar.setCursor(Qt.PointingHandCursor)
        self.btn_iniciar.setStyleSheet(estilo_btn_accion)
        self.btn_iniciar.clicked.connect(self._toggle_temporizador)
        
        self.btn_saltar = QPushButton(" SALTAR")
        self.btn_saltar.setIcon(qta.icon('fa5s.forward'))
        self.btn_saltar.setObjectName("btnSaltarPomodoro")
        self.btn_saltar.setCursor(Qt.PointingHandCursor)
        self.btn_saltar.setStyleSheet(estilo_btn_accion)
        self.btn_saltar.clicked.connect(self._saltar_fase)

        self.btn_reiniciar = QPushButton(" REINICIAR")
        self.btn_reiniciar.setIcon(qta.icon('fa5s.sync'))
        self.btn_reiniciar.setObjectName("btnReiniciarPomodoro")
        self.btn_reiniciar.setCursor(Qt.PointingHandCursor)
        self.btn_reiniciar.setStyleSheet(estilo_btn_accion)
        self.btn_reiniciar.clicked.connect(self._reiniciar_temporizador)

        layout_controles.addWidget(self.btn_iniciar)
        layout_controles.addWidget(self.btn_saltar)
        layout_controles.addWidget(self.btn_reiniciar)
        self.btn_silenciar = QPushButton(" SILENCIAR ALARMA")
        self.btn_silenciar.setIcon(qta.icon('fa5s.bell-slash'))
        self.btn_silenciar.setObjectName("btnSilenciarAlarma")
        self.btn_silenciar.setCursor(Qt.PointingHandCursor)
        self.btn_silenciar.setStyleSheet(estilo_btn_accion)
        self.btn_silenciar.clicked.connect(self._detener_alarma)
        self.btn_silenciar.hide()

        layout_reloj.addStretch()
        layout_reloj.addWidget(self.lbl_fase)
        layout_reloj.addWidget(self.lbl_tiempo)
        layout_reloj.addLayout(layout_controles)
        layout_reloj.addSpacing(15)
        layout_reloj.addWidget(self.btn_silenciar, 0, Qt.AlignCenter)
        layout_reloj.addStretch()
        panel_derecho = QWidget()
        panel_derecho.setObjectName("panelDerechoPomodoro")
        layout_derecho = QVBoxLayout(panel_derecho)
        layout_derecho.setContentsMargins(0, 0, 0, 0)
        layout_derecho.setSpacing(20)

        grupo_tiempos = QGroupBox("Tiempos (Minutos)")
        grupo_tiempos.setObjectName("grupoTiemposPomodoro")
        estilo_grupos = "QGroupBox { font-size: 15px; font-weight: bold; border-radius: 10px; margin-top: 15px; padding: 20px 15px 15px 15px; }"
        grupo_tiempos.setStyleSheet(estilo_grupos)
        
        grid_tiempos = QGridLayout(grupo_tiempos)
        grid_tiempos.setSpacing(20)

        self.sel_trabajo = NumberPicker("Trabajo:", 1, 120, 25, 'fa5s.laptop')
        self.sel_corto = NumberPicker("Desc. Corto:", 1, 60, 5, 'fa5s.coffee')
        self.sel_largo = NumberPicker("Desc. Largo:", 1, 60, 15, 'fa5s.couch')
        self.sel_sesiones = NumberPicker("Ciclos:", 1, 10, 4, 'fa5s.redo')

        grid_tiempos.addWidget(self.sel_trabajo, 0, 0)
        grid_tiempos.addWidget(self.sel_corto, 0, 1)
        grid_tiempos.addWidget(self.sel_largo, 1, 0)
        grid_tiempos.addWidget(self.sel_sesiones, 1, 1)

        self.sel_trabajo.valueChanged.connect(self._aplicar_configuracion_actual)
        self.sel_corto.valueChanged.connect(self._aplicar_configuracion_actual)
        self.sel_largo.valueChanged.connect(self._aplicar_configuracion_actual)

        grupo_alarma = QGroupBox("Alarma")
        grupo_alarma.setObjectName("grupoAlarmaPomodoro")
        grupo_alarma.setStyleSheet(estilo_grupos)
        layout_alarma = QHBoxLayout(grupo_alarma)
        
        self.lbl_ruta_alarma = QLabel("Alarma por defecto")
        self.lbl_ruta_alarma.setStyleSheet("font-size: 13px;")
        
        btn_alarma = QPushButton(" Elegir Audio")
        btn_alarma.setIcon(qta.icon('fa5s.music'))
        btn_alarma.setCursor(Qt.PointingHandCursor)
        btn_alarma.setStyleSheet("font-weight: bold; padding: 10px 15px; border-radius: 8px;")
        btn_alarma.clicked.connect(self._seleccionar_alarma)
        
        layout_alarma.addWidget(self.lbl_ruta_alarma, stretch=1)
        layout_alarma.addWidget(btn_alarma)

        grupo_perfiles = QGroupBox("Perfiles Guardados")
        grupo_perfiles.setObjectName("grupoPerfilesPomodoro")
        grupo_perfiles.setStyleSheet(estilo_grupos)
        layout_perfiles = QVBoxLayout(grupo_perfiles)
        
        self.combo_perfiles = QComboBox()
        self.combo_perfiles.setStyleSheet("font-size: 14px; padding: 10px; border-radius: 8px;")
        self.combo_perfiles.currentIndexChanged.connect(self._cargar_perfil_seleccionado)
        
        layout_guardar = QHBoxLayout()
        self.txt_nombre_perfil = QLineEdit()
        self.txt_nombre_perfil.setPlaceholderText("Nombre del nuevo perfil...")
        self.txt_nombre_perfil.setStyleSheet("font-size: 14px; padding: 10px; border-radius: 8px;")
        
        btn_guardar = QPushButton(" Guardar")
        btn_guardar.setIcon(qta.icon('fa5s.save'))
        btn_guardar.setCursor(Qt.PointingHandCursor)
        btn_guardar.setStyleSheet("font-weight: bold; padding: 10px; border-radius: 8px;")
        btn_guardar.clicked.connect(self._guardar_perfil)

        btn_eliminar = QPushButton("")
        btn_eliminar.setIcon(qta.icon('fa5s.trash'))
        btn_eliminar.setCursor(Qt.PointingHandCursor)
        btn_eliminar.setStyleSheet("font-weight: bold; padding: 10px; border-radius: 8px;")
        btn_eliminar.clicked.connect(self._eliminar_perfil)

        layout_guardar.addWidget(self.txt_nombre_perfil)
        layout_guardar.addWidget(btn_guardar)
        layout_guardar.addWidget(btn_eliminar)
        
        layout_perfiles.addWidget(self.combo_perfiles)
        layout_perfiles.addSpacing(10)
        layout_perfiles.addLayout(layout_guardar)

        layout_derecho.addWidget(grupo_tiempos)
        layout_derecho.addWidget(grupo_alarma)
        layout_derecho.addWidget(grupo_perfiles)
        layout_derecho.addStretch()

        layout_principal.addWidget(panel_izquierdo, stretch=4)
        layout_principal.addWidget(panel_derecho, stretch=5)

    def _toggle_temporizador(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_iniciar.setText(" REANUDAR")
            self.btn_iniciar.setIcon(qta.icon('fa5s.play'))
            self.btn_iniciar.setProperty("estado", "pausado")
        else:
            self.timer.start(1000)
            self.btn_iniciar.setText(" PAUSAR")
            self.btn_iniciar.setIcon(qta.icon('fa5s.pause'))
            self.btn_iniciar.setProperty("estado", "corriendo")
            
        self.btn_iniciar.style().unpolish(self.btn_iniciar)
        self.btn_iniciar.style().polish(self.btn_iniciar)

    def _reiniciar_temporizador(self):
        self.timer.stop()
        self._detener_alarma()
        self.btn_iniciar.setText(" INICIAR")
        self.btn_iniciar.setIcon(qta.icon('fa5s.play'))
        self.btn_iniciar.setProperty("estado", "detenido")
        
        self.btn_iniciar.style().unpolish(self.btn_iniciar)
        self.btn_iniciar.style().polish(self.btn_iniciar)
        
        self.fase_actual = "Trabajo"
        self.sesion_actual = 1
        self._aplicar_configuracion_actual()

    def _saltar_fase(self):
        self._detener_alarma()
        self._avanzar_siguiente_fase()

    def _aplicar_configuracion_actual(self):
        if not self.timer.isActive():
            if self.fase_actual == "Trabajo":
                self.tiempo_restante = self.sel_trabajo.value() * 60
            elif self.fase_actual == "Descanso Corto":
                self.tiempo_restante = self.sel_corto.value() * 60
            elif self.fase_actual == "Descanso Largo":
                self.tiempo_restante = self.sel_largo.value() * 60
        self._actualizar_etiquetas()

    def _tick_temporizador(self):
        if self.tiempo_restante > 0:
            self.tiempo_restante -= 1
            self._actualizar_etiquetas()
        else:
            self._finalizar_fase()

    def _actualizar_etiquetas(self):
        minutos, segundos = divmod(self.tiempo_restante, 60)
        self.lbl_tiempo.setText(f"{minutos:02}:{segundos:02}")
        self.lbl_fase.setText(f"{self.fase_actual} · Sesión {self.sesion_actual}/{self.sel_sesiones.value()}")

    def _finalizar_fase(self):
        self._reproducir_alarma()
        self._avanzar_siguiente_fase()
        
    def _avanzar_siguiente_fase(self):
        if self.fase_actual == "Trabajo":
            if self.sesion_actual % self.sel_sesiones.value() == 0:
                self.fase_actual = "Descanso Largo"
            else:
                self.fase_actual = "Descanso Corto"
        else:
            self.fase_actual = "Trabajo"
            self.sesion_actual += 1

        if self.fase_actual == "Trabajo":
            self.tiempo_restante = self.sel_trabajo.value() * 60
        elif self.fase_actual == "Descanso Corto":
            self.tiempo_restante = self.sel_corto.value() * 60
        elif self.fase_actual == "Descanso Largo":
            self.tiempo_restante = self.sel_largo.value() * 60
            
        self._actualizar_etiquetas()

    def _reproducir_alarma(self):
        if self.ruta_alarma and os.path.exists(self.ruta_alarma):
            # Se usa ruta absoluta para evitar problemas con QMediaPlayer en PySide6
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(self.ruta_alarma)))
            self.player.play()
            self.btn_silenciar.show()
            self.timer_alarma.start(5000)
        else:
            QApplication.beep()

    def _detener_alarma(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()
        self.timer_alarma.stop()
        self.btn_silenciar.hide()

    def _seleccionar_alarma(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Alarma", "", "Audio (*.mp3 *.wav *.ogg)")
        if ruta:
            self.ruta_alarma = ruta
            nombre_archivo = os.path.basename(ruta)
            self.lbl_ruta_alarma.setText(f"Cargado: {nombre_archivo[:20]}...")

    def _cargar_perfiles(self):
        self.combo_perfiles.blockSignals(True)
        self.combo_perfiles.clear()
        
        with open(ARCHIVO_PERFILES, "r", encoding="utf-8") as f:
            perfiles = json.load(f)
            
        for nombre in perfiles.keys():
            self.combo_perfiles.addItem(nombre)
            
        self.combo_perfiles.blockSignals(False)

    def _cargar_perfil_seleccionado(self):
        nombre = self.combo_perfiles.currentText()
        if not nombre: return
        
        with open(ARCHIVO_PERFILES, "r", encoding="utf-8") as f:
            perfiles = json.load(f)
            
        if nombre in perfiles:
            datos = perfiles[nombre]
            self.sel_trabajo.setValue(datos.get("trabajo", 25))
            self.sel_corto.setValue(datos.get("descanso_corto", 5))
            self.sel_largo.setValue(datos.get("descanso_largo", 15))
            self.sel_sesiones.setValue(datos.get("sesiones", 4))
            
            ruta_audio = datos.get("alarma", "")
            if ruta_audio and os.path.exists(ruta_audio):
                self.ruta_alarma = ruta_audio
                self.lbl_ruta_alarma.setText(f"Cargado: {os.path.basename(ruta_audio)[:20]}...")
            else:
                self.ruta_alarma = ""
                self.lbl_ruta_alarma.setText("Alarma por defecto")
                
            self._reiniciar_temporizador()

    def _guardar_perfil(self):
        nombre = self.txt_nombre_perfil.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "Ingresa un nombre para el perfil.")
            return
            
        with open(ARCHIVO_PERFILES, "r", encoding="utf-8") as f:
            perfiles = json.load(f)
            
        perfiles[nombre] = {
            "trabajo": self.sel_trabajo.value(),
            "descanso_corto": self.sel_corto.value(),
            "descanso_largo": self.sel_largo.value(),
            "sesiones": self.sel_sesiones.value(),
            "alarma": self.ruta_alarma
        }
        
        with open(ARCHIVO_PERFILES, "w", encoding="utf-8") as f:
            json.dump(perfiles, f, indent=4)
            
        self.txt_nombre_perfil.clear()
        self._cargar_perfiles()
        self.combo_perfiles.setCurrentText(nombre)

    def _eliminar_perfil(self):
        nombre = self.combo_perfiles.currentText()
        if not nombre: return
            
        if nombre == "Defecto":
            QMessageBox.warning(self, "Denegado", "El perfil 'Defecto' no se puede eliminar.")
            return

        respuesta = QMessageBox.question(
            self, "Confirmar", 
            f"¿Estás seguro de que deseas eliminar el perfil '{nombre}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            with open(ARCHIVO_PERFILES, "r", encoding="utf-8") as f:
                perfiles = json.load(f)
                
            if nombre in perfiles:
                del perfiles[nombre]
                
            with open(ARCHIVO_PERFILES, "w", encoding="utf-8") as f:
                json.dump(perfiles, f, indent=4)
                
            self._cargar_perfiles()
            self.combo_perfiles.setCurrentText("Defecto")

def cargar_addon():
    widget = PomodoroApp()
    return "Pomodoro", widget