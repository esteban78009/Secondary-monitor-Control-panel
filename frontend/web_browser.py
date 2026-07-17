import os
import webbrowser

# Forzar a qtawesome/qtpy a usar PySide6
os.environ["QT_API"] = "pyside6"
import qtawesome as qta

from PySide6.QtCore import QSize, Qt, QTimer, Slot, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from backend.web_browser_backend import create_new_page, load_pages, delete_page

class WebPAGE(QWidget): 
    def __init__(self, web_container, parent=None):
        super().__init__(parent)
        self.web_container = web_container
        
        self.setFixedSize(100, 130)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.btn_main = QPushButton()
        self.btn_main.setFixedSize(100, 100)
        self.btn_main.setObjectName("webPageButton")
        self.btn_main.setIcon(QIcon(self.web_container.logo))
        self.btn_main.setIconSize(QSize(90, 90))
        self.btn_main.setCursor(Qt.PointingHandCursor)
        self.btn_main.clicked.connect(self._procesar_click)
        
        self.btn_delete = QPushButton("")
        self.btn_delete.setObjectName("btnDelete")
        self.btn_delete.setIcon(qta.icon('fa5s.trash'))
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet("""
            QPushButton { border-radius: 4px; padding: 4px; font-weight: bold; }
        """)
        self.btn_delete.clicked.connect(self._eliminar_pagina)
        self.btn_delete.hide() 

        layout.addWidget(self.btn_main)
        layout.addWidget(self.btn_delete)

    def set_modo_eliminar(self, activado):
        self.btn_delete.setVisible(activado)

    @Slot()
    def _procesar_click(self):
        self.btn_main.setEnabled(False)
        self.ejecutar_accion()
        QTimer.singleShot(500, self._cooldown)

    def ejecutar_accion(self):
        url = self.web_container.url
        if os.path.exists(url):
            os.startfile(url)
        else:
            webbrowser.open(url)

    @Slot()
    def _cooldown(self):
        self.btn_main.setEnabled(True)
        
    @Slot()
    def _eliminar_pagina(self):
        delete_page(self.web_container.file_path)
        self.deleteLater()

class AddWebPage(QWidget):
    actualizar_lista = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("addWebPagePanel")
        self.setFixedWidth(320) 
        
        self.setStyleSheet("""
            QWidget#addWebPagePanel { border-radius: 10px; }
            QLabel { font-weight: bold; }
            QLineEdit { border-radius: 6px; padding: 6px; }
        """)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)

        self.preview = QLabel("sin imagen")
        self.preview.setObjectName("addWebPagePreview")
        self.preview.setFixedSize(80, 80)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setScaledContents(True) 
        layout_principal.addWidget(self.preview, alignment=Qt.AlignCenter)
        layout_principal.addSpacing(20)

        layout_principal.addWidget(QLabel("URL o Ejecutable:"))
        layout_url = QHBoxLayout()
        
        self.entrada_url = QLineEdit()
        self.entrada_url.setObjectName("entradaUrl")
        self.entrada_url.setPlaceholderText("ej: https://... o C:\\App.exe")
        
        btn_examinar_style = "QPushButton { border-radius: 6px; padding: 6px; }"
        
        btn_examinar_exe = QPushButton("")
        btn_examinar_exe.setObjectName("btnExaminarExe")
        btn_examinar_exe.setIcon(qta.icon('fa5s.search'))
        btn_examinar_exe.setCursor(Qt.PointingHandCursor)
        btn_examinar_exe.setStyleSheet(btn_examinar_style)
        btn_examinar_exe.clicked.connect(self.explorer_exe)

        layout_url.addWidget(self.entrada_url)
        layout_url.addWidget(btn_examinar_exe)
        layout_principal.addLayout(layout_url)
        layout_principal.addSpacing(10)

        layout_principal.addWidget(QLabel("Ruta de la imagen:"))
        
        layout_file = QHBoxLayout()
        self.entrada_archivo = QLineEdit()
        self.entrada_archivo.setObjectName("entradaArchivo")
        self.entrada_archivo.setPlaceholderText("Selecciona una imagen...")
        
        btn_examinar = QPushButton("")
        btn_examinar.setObjectName("btnExaminar")
        btn_examinar.setIcon(qta.icon('fa5s.folder'))
        btn_examinar.setCursor(Qt.PointingHandCursor)
        btn_examinar.setStyleSheet(btn_examinar_style)
        btn_examinar.clicked.connect(self.explorer)
        
        layout_file.addWidget(self.entrada_archivo)
        layout_file.addWidget(btn_examinar)
        layout_principal.addLayout(layout_file)
        
        layout_principal.addStretch() 

        layout_botones = QHBoxLayout()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnCancelar")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; border-radius: 6px; }")
        btn_cancelar.clicked.connect(self.cerrar_panel)

        btn_aceptar = QPushButton("Guardar")
        btn_aceptar.setObjectName("btnAceptar")
        btn_aceptar.setCursor(Qt.PointingHandCursor)
        btn_aceptar.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; border-radius: 6px; }")
        btn_aceptar.clicked.connect(self.save_data)

        layout_botones.addWidget(btn_cancelar)
        layout_botones.addWidget(btn_aceptar)
        
        layout_principal.addLayout(layout_botones)

    def explorer_exe(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, 
            "Seleccionar programa o acceso directo", 
            "", 
            "Ejecutables y Accesos directos (*.exe *.lnk);;Todos los archivos (*)"
        )
        if ruta:
            self.entrada_url.setText(os.path.normpath(ruta))

    def explorer(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, 
            "Seleccionar imagen", 
            "", 
            "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos los archivos (*)"
        )
        if ruta:
            self.entrada_archivo.setText(os.path.normpath(ruta))

    def cerrar_panel(self):
        self.entrada_url.clear()
        self.entrada_archivo.clear()
        self.hide()

    def save_data(self):
        url = self.entrada_url.text().strip()
        ruta_local = self.entrada_archivo.text().strip()
        
        if url and ruta_local:
            create_new_page(url, ruta_local)
            
        self.cerrar_panel()
        self.actualizar_lista.emit() 

GENERADOR = (WebPAGE(i) for i in load_pages())