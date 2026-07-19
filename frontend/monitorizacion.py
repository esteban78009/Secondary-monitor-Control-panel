import os
import sys

# Forzar a qtawesome/qtpy a usar PySide6
os.environ["QT_API"] = "pyside6"
import qtawesome as qta

import psutil
import wmi
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                               QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont

# Constante para cálculo de Gigabytes
GB = 1024**3

class MonitorSistema(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("monitorSistemaWindow")
        self.setWindowTitle("Monitor de Hardware Completo")
        self.setFixedSize(380, 550)

        scroll = QScrollArea()
        scroll.setObjectName("monitorScroll")
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)
        
        widget_central = QWidget()
        widget_central.setObjectName("monitorContenido")
        self.layout = QVBoxLayout(widget_central)
        scroll.setWidget(widget_central)

        self.fuente_titulo = QFont("Arial", 11, QFont.Bold)
        self.fuente_datos = QFont("Consolas", 10)

        # PROCESADOR
        self.layout.addWidget(self.crear_titulo("PROCESADOR", 'fa5s.microchip'))
        self.lbl_cpu_uso = self.crear_label("CPU Uso: Calculando...")
        self.lbl_cpu_temp = self.crear_label("CPU Temp: Esperando OHM...")
        self.layout.addWidget(self.lbl_cpu_uso)
        self.layout.addWidget(self.lbl_cpu_temp)
        self.layout.addWidget(self.crear_separador())

        # MEMORIA RAM
        self.layout.addWidget(self.crear_titulo("MEMORIA RAM", 'fa5s.memory'))
        self.lbl_ram = self.crear_label("RAM Uso: Calculando...")
        self.layout.addWidget(self.lbl_ram)
        self.layout.addWidget(self.crear_separador())

        # TARJETA GRÁFICA
        self.layout.addWidget(self.crear_titulo("TARJETA GRÁFICA", 'fa5s.desktop'))
        self.lbl_gpu_uso = self.crear_label("GPU Uso: Esperando OHM...")
        self.lbl_gpu_temp = self.crear_label("GPU Temp: Esperando OHM...")
        self.layout.addWidget(self.lbl_gpu_uso)
        self.layout.addWidget(self.lbl_gpu_temp)
        self.layout.addWidget(self.crear_separador())

        # ALMACENAMIENTO
        self.layout.addWidget(self.crear_titulo("ALMACENAMIENTO", 'fa5s.hdd'))
        self.disk_labels = {} 
        self.layout.addStretch()

        # OpenHardwareMonitor
        try:
            self.hw_monitor = wmi.WMI(namespace=r"root\OpenHardwareMonitor")
            self.ohm_activo = True
        except Exception:
            self.ohm_activo = False
            error_msg = "Error (Abre OpenHardwareMonitor)"
            self.lbl_cpu_temp.setText(f"CPU Temp: {error_msg}")
            self.lbl_gpu_uso.setText(f"GPU Uso: {error_msg}")
            self.lbl_gpu_temp.setText(f"GPU Temp: {error_msg}")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_datos)
        self.timer.start(1500)

    def showEvent(self, event):
        # Si el usuario vuelve a esta sección, reanudamos el muestreo.
        if not self.timer.isActive():
            self.timer.start(1500)
        super().showEvent(event)

    def hideEvent(self, event):
        # Al salir de la sección (main.py la oculta dentro del QStackedWidget
        # en vez de destruirla) detenemos el timer, para no seguir leyendo
        # psutil/WMI cada 1.5s en segundo plano cuando nadie está mirando el
        # monitor. Esto es lo que causaba los picos de CPU intermitentes
        # aunque no estuvieras usando esa pantalla.
        self.timer.stop()
        super().hideEvent(event)

    def crear_titulo(self, texto, icono_str=None):
        if icono_str:
            container = QWidget()
            container.setObjectName("monitorSeccionContenedor")
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            
            lbl_icon = QLabel()
            lbl_icon.setObjectName("monitorIconoLabel")
            # Convertimos el icono en Pixmap (Se eliminó el color quemado para adaptabilidad QSS)
            lbl_icon.setPixmap(qta.icon(icono_str).pixmap(18, 18))
            
            lbl_texto = QLabel(texto)
            lbl_texto.setObjectName("monitorSeccionTitulo")
            lbl_texto.setFont(self.fuente_titulo)
            
            layout.addWidget(lbl_icon)
            layout.addWidget(lbl_texto)
            layout.addStretch()
            return container
        else:
            lbl = QLabel(texto)
            lbl.setObjectName("monitorSeccionTitulo")
            lbl.setFont(self.fuente_titulo)
            return lbl

    def crear_label(self, texto):
        lbl = QLabel(texto)
        lbl.setObjectName("monitorDatoLabel")
        lbl.setFont(self.fuente_datos)
        return lbl

    def crear_separador(self):
        linea = QFrame()
        linea.setObjectName("monitorSeparador")
        linea.setFrameShape(QFrame.HLine)
        linea.setFrameShadow(QFrame.Sunken)
        return linea

    def actualizar_datos(self):
        # 1. CPU
        self.lbl_cpu_uso.setText(f"CPU Uso: {psutil.cpu_percent()}%")

        # 2. RAM
        ram = psutil.virtual_memory()
        self.lbl_ram.setText(f"RAM Uso: {ram.percent}% ({ram.used / GB:.1f} GB / {ram.total / GB:.1f} GB)")

        # 3. Discos
        for part in psutil.disk_partitions():
            if 'cdrom' in part.opts or not part.fstype: 
                continue
            
            try:
                usage = psutil.disk_usage(part.mountpoint)
                texto = f"[{part.device}] {usage.percent}% ({usage.used // GB}GB / {usage.total // GB}GB)"
                
                if part.device not in self.disk_labels:
                    lbl = self.crear_label(texto)
                    self.layout.insertWidget(self.layout.count() - 1, lbl)
                    self.disk_labels[part.device] = lbl
                else:
                    self.disk_labels[part.device].setText(texto)
            except PermissionError:
                continue

        # 4. OHM (Temperaturas y GPU)
        if self.ohm_activo:
            try:
                temp_cpu_encontrada = False
                
                for sensor in self.hw_monitor.Sensor():
                    if sensor.SensorType == 'Temperature':
                        if not temp_cpu_encontrada and ('CPU Package' in sensor.Name or 'CPU Core' in sensor.Name):
                            self.lbl_cpu_temp.setText(f"CPU Temp: {int(sensor.Value)}°C")
                            temp_cpu_encontrada = True
                        elif 'GPU Core' in sensor.Name:
                            self.lbl_gpu_temp.setText(f"GPU Temp: {int(sensor.Value)}°C")
                            
                    elif sensor.SensorType == 'Load' and 'GPU Core' in sensor.Name:
                        self.lbl_gpu_uso.setText(f"GPU Uso: {int(sensor.Value)}%")
            except Exception as e:
                print(f"Error silencioso leyendo OHM: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = MonitorSistema()
    ventana.show()
    sys.exit(app.exec())