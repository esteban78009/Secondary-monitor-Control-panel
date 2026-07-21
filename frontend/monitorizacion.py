import os
import sys
import json
import time
import urllib.request
import re

# Forzar a qtawesome/qtpy a usar PySide6
os.environ["QT_API"] = "pyside6"
import qtawesome as qta

import psutil
import wmi
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                               QVBoxLayout, QHBoxLayout, QGridLayout, 
                               QLabel, QFrame, QScrollArea, QProgressBar, QPushButton)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont

GB = 1024**3
MB = 1024**2

class MonitorSistema(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("monitorSistemaWindow")
        self.setWindowTitle("Monitor de Hardware")
        self.setMinimumSize(420, 600)

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

        self.detalles_visibles = False

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch()
        self.btn_detalles = QPushButton("⚙ Detalles")
        self.btn_detalles.setFixedSize(90, 26)
        self.btn_detalles.setStyleSheet("font-size: 11px;")
        self.btn_detalles.clicked.connect(self.toggle_detalles)
        top_layout.addWidget(self.btn_detalles)
        self.layout.addLayout(top_layout)

        self.layout.addWidget(self.crear_titulo("PROCESADOR", 'fa5s.microchip'))
        self.lbl_cpu_uso = self.crear_label("CPU Uso Total: Calculando...")
        self.lbl_cpu_temp = self.crear_label("CPU Temp: Esperando sensor...")
        self.layout.addWidget(self.lbl_cpu_uso)
        self.layout.addWidget(self.lbl_cpu_temp)
        self.widget_cpu_grid = QWidget()
        self.grid_cpu = QGridLayout(self.widget_cpu_grid)
        self.grid_cpu.setContentsMargins(5, 5, 0, 5)
        self.grid_cpu.setHorizontalSpacing(15)
        self.grid_cpu.setVerticalSpacing(3)
        
        self.labels_cores = []
        n_logicos = psutil.cpu_count(logical=True)
        for i in range(n_logicos):
            container_nucleo, lbl = self.crear_label_con_icono(f"{i+1}° Calc...", 'fa5s.microchip', 12)
            lbl.setStyleSheet("font-size: 11px;")
            self.grid_cpu.addWidget(container_nucleo, i // 2, i % 2, alignment=Qt.AlignLeft)
            self.labels_cores.append(lbl)
            
        self.grid_cpu.setColumnStretch(2, 1) 
        
        self.widget_cpu_grid.hide()
        self.layout.addWidget(self.widget_cpu_grid)
        self.layout.addWidget(self.crear_separador())

        self.layout.addWidget(self.crear_titulo("MEMORIA RAM", 'fa5s.memory'))
        self.lbl_ram = self.crear_label("RAM: Calculando...")
        self.bar_ram = QProgressBar()
        self.bar_ram.setFixedHeight(14)
        self.layout.addWidget(self.lbl_ram)
        self.layout.addWidget(self.bar_ram)
        self.layout.addWidget(self.crear_separador())

        self.layout.addWidget(self.crear_titulo("TARJETA GRÁFICA", 'mdi.expansion-card'))
        self.lbl_gpu_uso = self.crear_label("GPU Uso: Esperando sensor...")
        self.lbl_gpu_temp = self.crear_label("GPU Temp: Esperando sensor...")
        self.lbl_vram_uso = self.crear_label("VRAM: Esperando sensor...")
        self.bar_vram = QProgressBar()
        self.bar_vram.setFixedHeight(14)
        
        self.layout.addWidget(self.lbl_gpu_uso)
        self.layout.addWidget(self.lbl_gpu_temp)
        self.layout.addWidget(self.lbl_vram_uso)
        self.layout.addWidget(self.bar_vram)
        self.layout.addWidget(self.crear_separador())

        self.layout.addWidget(self.crear_titulo("ALMACENAMIENTO", 'fa5s.hdd'))
        self.disk_widgets = {}
        self.layout.addStretch()

        # Variables WMI / I-O
        self.last_disk_io = psutil.disk_io_counters(perdisk=True)
        self.last_time = time.time()

        self.wmi_lhm = None
        self.wmi_ohm = None
        
        self.wmi_cimv2 = None
        if os.name == 'nt':
            try: self.wmi_cimv2 = wmi.WMI()
            except Exception: pass

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_datos)
        self.timer.start(1500)

    def showEvent(self, event):
        if not self.timer.isActive():
            self.timer.start(1500)
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def toggle_detalles(self):
        self.detalles_visibles = not self.detalles_visibles
        
        if self.detalles_visibles:
            self.widget_cpu_grid.show()
            self.btn_detalles.setStyleSheet("font-size: 11px; font-weight: bold; background-color: #555;")
        else:
            self.widget_cpu_grid.hide()
            self.btn_detalles.setStyleSheet("font-size: 11px; background-color: transparent;")
            
        self.actualizar_datos() 

    # --- UI HELPERS ---
    def crear_titulo(self, texto, icono_str=None):
        if icono_str:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            lbl_icon = QLabel()
            try:
                lbl_icon.setPixmap(qta.icon(icono_str).pixmap(18, 18))
            except Exception:
                lbl_icon.setPixmap(qta.icon('fa5s.microchip').pixmap(18, 18))
            
            lbl_texto = QLabel(texto)
            lbl_texto.setFont(self.fuente_titulo)
            layout.addWidget(lbl_icon)
            layout.addWidget(lbl_texto)
            layout.addStretch()
            return container
        else:
            lbl = QLabel(texto)
            lbl.setFont(self.fuente_titulo)
            return lbl

    def crear_label(self, texto):
        lbl = QLabel(texto)
        lbl.setFont(self.fuente_datos)
        return lbl

    def crear_label_con_icono(self, texto, icono_str, icon_size=14):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        lbl_icon = QLabel()
        try:
            lbl_icon.setPixmap(qta.icon(icono_str).pixmap(icon_size, icon_size))
        except Exception:
            pass
            
        lbl_texto = QLabel(texto)
        lbl_texto.setFont(self.fuente_datos)
        
        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_texto)
        layout.addStretch()
        
        return container, lbl_texto

    def crear_separador(self):
        linea = QFrame()
        linea.setFrameShape(QFrame.HLine)
        linea.setFrameShadow(QFrame.Sunken)
        return linea

    # --- LECTURA DE SENSORES ---
    def procesar_nombre_core(self, nombre, val, stats):
        try:
            match = re.search(r'core.*?#?(\d+)', nombre)
            if match:
                idx = int(match.group(1)) - 1
                stats["core_temps"][idx] = val
        except: pass

    def extraer_wmi(self, obj_wmi, stats):
        try:
            sensores = obj_wmi.Sensor()
            if len(sensores) == 0: return False
            for sensor in sensores:
                nombre = sensor.Name.lower()
                tipo = sensor.SensorType
                val = float(sensor.Value)
                
                if tipo == 'Temperature':
                    if stats["cpu_temp"] is None and any(x in nombre for x in ['cpu package', 'core (tctl']):
                        stats["cpu_temp"] = val
                    elif 'cpu core' in nombre:
                        self.procesar_nombre_core(nombre, val, stats)
                    elif stats["gpu_temp"] is None and 'gpu core' in nombre:
                        stats["gpu_temp"] = val
                elif tipo == 'Load':
                    if stats["gpu_uso"] is None and 'gpu core' in nombre:
                        stats["gpu_uso"] = val
                    elif stats["vram_uso"] is None and any(x in nombre for x in ['gpu memory', 'frame buffer']):
                        stats["vram_uso"] = val
                elif tipo in ['SmallData', 'Data']:
                    if 'gpu memory used' in nombre: stats['vram_used_mb'] = val
                    elif 'gpu memory free' in nombre: stats['vram_free_mb'] = val
                    elif 'gpu memory total' in nombre: stats['vram_total_mb'] = val
                        
            return any(v is not None for v in stats.values())
        except Exception: return False

    def extraer_datos_http(self, nodo, stats):
        nombre = nodo.get("Text", "").lower()
        valor_str = nodo.get("Value", "")

        if "°c" in valor_str.lower():
            try:
                val = float(valor_str.replace(",", ".").split(" ")[0])
                if stats["cpu_temp"] is None and any(x in nombre for x in ['cpu package', 'core (tctl']):
                    stats["cpu_temp"] = val
                elif 'cpu core' in nombre:
                    self.procesar_nombre_core(nombre, val, stats)
                elif stats["gpu_temp"] is None and 'gpu core' in nombre:
                    stats["gpu_temp"] = val
            except ValueError: pass
                
        elif "%" in valor_str:
            try:
                val = float(valor_str.replace(",", ".").split(" ")[0])
                if stats["gpu_uso"] is None and 'gpu core' in nombre:
                    stats["gpu_uso"] = val
                elif stats["vram_uso"] is None and any(x in nombre for x in ['gpu memory', 'frame buffer']):
                    stats["vram_uso"] = val
            except ValueError: pass
            
        elif "mb" in valor_str.lower() and "memory" in nombre:
            try:
                val = float(valor_str.replace(",", ".").split(" ")[0])
                if 'used' in nombre: stats['vram_used_mb'] = val
                elif 'free' in nombre: stats['vram_free_mb'] = val
                elif 'total' in nombre: stats['vram_total_mb'] = val
            except ValueError: pass

        for hijo in nodo.get("Children", []):
            self.extraer_datos_http(hijo, stats)

    def actualizar_datos(self):
        # 1. CPU
        self.lbl_cpu_uso.setText(f"CPU Uso Total: {psutil.cpu_percent()}%")

        # 2. RAM
        ram = psutil.virtual_memory()
        self.lbl_ram.setText(f"RAM: {ram.used / GB:.1f} GB usados / {ram.available / GB:.1f} GB libres")
        self.bar_ram.setValue(int(ram.percent))
        self.bar_ram.setFormat(f"Ocupado: {ram.percent}%")

        # 3. SENSORES
        stats = {
            "cpu_temp": None, "gpu_temp": None, "gpu_uso": None, "vram_uso": None, 
            "vram_used_mb": None, "vram_free_mb": None, "vram_total_mb": None,
            "core_temps": {}
        }
        datos_leidos = False

        if not self.wmi_lhm:
            try: self.wmi_lhm = wmi.WMI(namespace=r"root\LibreHardwareMonitor")
            except Exception: pass
        if self.wmi_lhm: datos_leidos = self.extraer_wmi(self.wmi_lhm, stats)

        if not datos_leidos:
            try:
                req = urllib.request.urlopen("http://localhost:8085/data.json", timeout=0.3)
                data = json.loads(req.read().decode())
                self.extraer_datos_http(data, stats)
                if any(v is not None for v in stats.values()) or stats["core_temps"]: 
                    datos_leidos = True
            except Exception: pass

        if not datos_leidos:
            if not self.wmi_ohm:
                try: self.wmi_ohm = wmi.WMI(namespace=r"root\OpenHardwareMonitor")
                except Exception: pass
            if self.wmi_ohm: datos_leidos = self.extraer_wmi(self.wmi_ohm, stats)

        # 4. ACTUALIZAR INTERFAZ SENSORES
        if datos_leidos:
            if stats["cpu_temp"] is not None: self.lbl_cpu_temp.setText(f"CPU Temp: {int(stats['cpu_temp'])}°C")
            if stats["gpu_uso"] is not None:  self.lbl_gpu_uso.setText(f"GPU Uso: {int(stats['gpu_uso'])}%")
            if stats["gpu_temp"] is not None: self.lbl_gpu_temp.setText(f"GPU Temp: {int(stats['gpu_temp'])}°C")
            
            if stats["vram_uso"] is not None:
                val_vram = int(stats["vram_uso"])
                used_gb = (stats["vram_used_mb"] / 1024.0) if stats["vram_used_mb"] else 0.0
                total_gb = (stats["vram_total_mb"] / 1024.0) if stats["vram_total_mb"] else 0.0
                free_gb = (stats["vram_free_mb"] / 1024.0) if stats["vram_free_mb"] else 0.0
                
                if free_gb == 0.0 and total_gb > 0.0: free_gb = total_gb - used_gb
                elif total_gb == 0.0 and free_gb > 0.0: total_gb = used_gb + free_gb

                if used_gb > 0 and free_gb > 0:
                    self.lbl_vram_uso.setText(f"VRAM: {used_gb:.1f} GB usados / {free_gb:.1f} GB libres")
                else:
                    self.lbl_vram_uso.setText(f"VRAM Uso: {val_vram}%")

                self.bar_vram.setValue(val_vram)
                self.bar_vram.setFormat(f"Ocupado: {val_vram}%")
        else:
            msg_error = "Esperando (Abre LHM/OHM)"
            self.lbl_cpu_temp.setText(f"CPU Temp: {msg_error}")
            self.lbl_gpu_uso.setText(f"GPU Uso: {msg_error}")
            self.lbl_gpu_temp.setText(f"GPU Temp: {msg_error}")
            self.lbl_vram_uso.setText(f"VRAM: {msg_error}")
            self.bar_vram.setValue(0)
            self.bar_vram.setFormat("Sin conexión")

        # 5. ACTUALIZAR GRILLA CPU
        if self.detalles_visibles:
            usos_cores = psutil.cpu_percent(percpu=True)
            global_freq = psutil.cpu_freq()
            global_ghz = (global_freq.current / 1000.0) if global_freq else 0.0
            
            try: freqs = psutil.cpu_freq(percpu=True)
            except Exception: freqs = []

            for i, (uso, lbl) in enumerate(zip(usos_cores, self.labels_cores)):
                freq_ghz = (freqs[i].current / 1000.0) if (freqs and i < len(freqs) and freqs[i]) else 0.0
                if freq_ghz < 0.1: freq_ghz = global_ghz
                
                temp = stats["core_temps"].get(i, stats.get("cpu_temp"))
                temp_str = f"{int(temp)}°C" if temp is not None else "--°C"

                lbl.setText(f"{i+1}° {freq_ghz:.2f}GHz | {uso:02.0f}% | {temp_str}")

        # 6. DISCOS (Iconos + Lectura/Escritura WMI)
        disk_io_data = {}
        if self.detalles_visibles and self.wmi_cimv2:
            try:
                for d in self.wmi_cimv2.Win32_PerfFormattedData_PerfDisk_LogicalDisk():
                    disk_io_data[d.Name] = {
                        'read': float(d.DiskReadBytesPersec) / MB,
                        'write': float(d.DiskWriteBytesPersec) / MB,
                        'act': min(100.0, float(d.PercentDiskTime))
                    }
            except Exception: pass

        for part in psutil.disk_partitions():
            if 'cdrom' in part.opts or not part.fstype: continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                pct = usage.percent
                
                texto = f"[{part.device}] Usado: {usage.used/GB:.1f}GB | Libre: {usage.free/GB:.1f}GB | Total: {usage.total/GB:.1f}GB"
                
                if self.detalles_visibles:
                    drive_letter = part.mountpoint[:2]
                    if drive_letter in disk_io_data:
                        io = disk_io_data[drive_letter]
                        texto += f"  |  Act: {io['act']:.0f}%  L: {io['read']:.1f} MB/s  E: {io['write']:.1f} MB/s"

                if part.device not in self.disk_widgets:
                    container_disco, lbl = self.crear_label_con_icono(texto, 'fa5s.hdd', 14)
                    barra = QProgressBar()
                    barra.setFixedHeight(14)
                    
                    self.layout.insertWidget(self.layout.count() - 1, container_disco)
                    self.layout.insertWidget(self.layout.count() - 1, barra)
                    
                    self.disk_widgets[part.device] = {'lbl': lbl, 'barra': barra}
                else:
                    self.disk_widgets[part.device]['lbl'].setText(texto)
                    self.disk_widgets[part.device]['barra'].setValue(int(pct))
                    self.disk_widgets[part.device]['barra'].setFormat(f"Capacidad Ocupada: {pct}%")
            except PermissionError: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = MonitorSistema()
    ventana.show()
    sys.exit(app.exec())