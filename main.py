import sys
import os

# Forzar a qtawesome/qtpy a usar PySide6 para evitar conflictos de tipos con QIcon
os.environ["QT_API"] = "pyside6"

import importlib.util
import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from backend.web_browser_backend import load_pages
from backend.wallpaper_backend import aplicar_tema_guardado_o_por_defecto
from frontend.web_browser import AddWebPage, WebPAGE
from frontend.music_manager import MusicManager
from frontend.monitorizacion import MonitorSistema
from frontend.wallpaper import WallpaperConfiguratorWindow, SelectorTema
# --------------------------

class SeccionConVuelta(QWidget):


    def __init__(self, titulo, contenido: QWidget, volver_callback, parent=None):
        super().__init__(parent)
        self.setObjectName("seccionConVuelta")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        barra = QWidget()
        barra.setObjectName("barraSeccion")
        barra_layout = QHBoxLayout(barra)
        barra_layout.setContentsMargins(8, 8, 8, 8)

        btn_volver = QPushButton(" Volver al menú")
        btn_volver.setIcon(qta.icon('fa5s.arrow-left'))
        btn_volver.setObjectName("btnVolver")
        btn_volver.setCursor(Qt.PointingHandCursor)
        btn_volver.clicked.connect(volver_callback)

        label_titulo = QLabel(titulo)
        label_titulo.setObjectName("tituloSeccionActual")

        barra_layout.addWidget(btn_volver)
        barra_layout.addStretch()
        barra_layout.addWidget(label_titulo)
        barra_layout.addStretch()

        layout.addWidget(barra)
        layout.addWidget(contenido, 1)


class MenuPrincipal(QWidget):

    COLUMNAS = 4

    def __init__(self, ir_a_musica, ir_a_wallpapers, ir_a_monitor, parent=None):
        super().__init__(parent)
        self.setObjectName("menuPrincipal")

        layout_raiz = QVBoxLayout(self)

        self.scroll_iconos = QScrollArea()
        self.scroll_iconos.setObjectName("scrollIconos")
        self.scroll_iconos.setWidgetResizable(True)
        self.scroll_iconos.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_iconos.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_iconos.setFixedHeight(65)
        self.scroll_iconos.setStyleSheet("QScrollArea { border: none; }")

        self.contenedor_iconos = QWidget()
        self.contenedor_iconos.setObjectName("contenedorIconos")
        self.layout_iconos = QHBoxLayout(self.contenedor_iconos)
        self.layout_iconos.setContentsMargins(0, 0, 0, 0)

        # Botones nativos
        self.btn_musica = QPushButton(" Música")
        self.btn_musica.setIcon(qta.icon('fa5s.music'))
        
        self.btn_wallpapers = QPushButton(" Wallpapers")
        self.btn_wallpapers.setIcon(qta.icon('fa5s.image'))
        
        self.btn_monitor = QPushButton(" Monitor")
        self.btn_monitor.setIcon(qta.icon('fa5s.desktop'))
        
        self.btn_tema = QPushButton(" Tema")
        self.btn_tema.setIcon(qta.icon('fa5s.palette'))

        for btn in (self.btn_musica, self.btn_wallpapers, self.btn_monitor, self.btn_tema):
            btn.setObjectName("btnAccesoDirecto")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(40)

        self.btn_musica.clicked.connect(ir_a_musica)
        self.btn_wallpapers.clicked.connect(ir_a_wallpapers)
        self.btn_monitor.clicked.connect(ir_a_monitor)
        self.btn_tema.clicked.connect(self.abrir_selector_tema)


        self.layout_iconos.addWidget(self.btn_musica)
        self.layout_iconos.addWidget(self.btn_wallpapers)
        self.layout_iconos.addWidget(self.btn_monitor)
        
        self.layout_iconos.addStretch() 
        
        self.layout_iconos.addWidget(self.btn_tema)

        self.scroll_iconos.setWidget(self.contenedor_iconos)
        layout_raiz.addWidget(self.scroll_iconos)

        encabezado = QWidget()
        encabezado.setObjectName("encabezadoWebpages")
        layout_encabezado = QHBoxLayout(encabezado)

        titulo = QLabel("")
        titulo.setObjectName("tituloSeccion")

        self.btn_toggle_borrar = QPushButton(" Editar Páginas")
        self.btn_toggle_borrar.setIcon(qta.icon('fa5s.edit'))
        self.btn_toggle_borrar.setObjectName("btnToggleBorrar")
        self.btn_toggle_borrar.setProperty("estado", "normal") 
        self.btn_toggle_borrar.setCheckable(True) 
        self.btn_toggle_borrar.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_borrar.setStyleSheet("""
            QPushButton { padding: 8px 12px; border-radius: 6px; font-weight: bold; }
        """)
        self.btn_toggle_borrar.clicked.connect(self.toggle_edicion_paginas)

        self.btn_agregar = QPushButton("")
        self.btn_agregar.setIcon(qta.icon('fa5s.plus'))
        self.btn_agregar.setObjectName("btnAgregarPagina")
        self.btn_agregar.setFixedSize(36, 36)
        self.btn_agregar.setCursor(Qt.PointingHandCursor)
        self.btn_agregar.setToolTip("Agregar nueva página web")
        self.btn_agregar.clicked.connect(self.abrir_creador)

        layout_encabezado.addWidget(titulo)
        layout_encabezado.addStretch()
        layout_encabezado.addWidget(self.btn_toggle_borrar) 
        layout_encabezado.addWidget(self.btn_agregar)

        layout_raiz.addWidget(encabezado)

        self.contenedor_principal = QWidget()
        self.contenedor_principal.setObjectName("contenedorPrincipal")
        layout_central = QHBoxLayout(self.contenedor_principal)
        layout_central.setContentsMargins(0, 10, 0, 0)
        layout_central.setSpacing(15)
        
        self.scroll = QScrollArea()
        self.scroll.setObjectName("scrollWebpages")
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; }") 

        self.contenedor_botones = QWidget()
        self.contenedor_botones.setObjectName("contenedorBotones")
        self.grid_botones = QGridLayout(self.contenedor_botones)
        self.grid_botones.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll.setWidget(self.contenedor_botones)
        
        self.panel_creador = AddWebPage()
        self.panel_creador.setObjectName("panelCreador")
        self.panel_creador.hide() 
        self.panel_creador.actualizar_lista.connect(self.recargar_botones)
        
        self.panel_tema = SelectorTema()
        self.panel_tema.hide()
        
        layout_central.addWidget(self.scroll, 1)
        layout_central.addWidget(self.panel_creador) 
        layout_central.addWidget(self.panel_tema) # Añadimos el nuevo panel al layout

        layout_raiz.addWidget(self.contenedor_principal, 1)

        self.recargar_botones()

    def agregar_boton_addon(self, nombre_addon, callback):
        btn_addon = QPushButton(f" {nombre_addon}")
        btn_addon.setIcon(qta.icon('fa5s.puzzle-piece'))
        btn_addon.setObjectName("btnAccesoDirecto")
        btn_addon.setCursor(Qt.PointingHandCursor)
        btn_addon.setMinimumHeight(40)
        btn_addon.clicked.connect(callback)
        

        posicion = self.layout_iconos.count() - 2
        self.layout_iconos.insertWidget(posicion, btn_addon)




    def abrir_creador(self):
        if self.panel_creador.isHidden():
            self.panel_tema.hide() 
            self.panel_creador.show()
        else:
            self.panel_creador.cerrar_panel() 

    def abrir_selector_tema(self):
        if self.panel_tema.isHidden():
            self.panel_creador.hide() 
            self.panel_tema.show()
        else:
            self.panel_tema.hide()

    def recargar_botones(self):
        if hasattr(self, 'btn_toggle_borrar') and self.btn_toggle_borrar.isChecked():
            self.btn_toggle_borrar.setChecked(False)
            self.toggle_edicion_paginas(False)

        while self.grid_botones.count():
            item = self.grid_botones.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for i, pagina in enumerate(load_pages()):
            boton = WebPAGE(pagina)
            fila, columna = divmod(i, self.COLUMNAS)
            self.grid_botones.addWidget(boton, fila, columna)

    def toggle_edicion_paginas(self, activado):
        if activado:
            self.btn_toggle_borrar.setText(" Terminar Edición")
            self.btn_toggle_borrar.setIcon(qta.icon('fa5s.check'))
            self.btn_toggle_borrar.setProperty("estado", "editando")
        else:
            self.btn_toggle_borrar.setText(" Editar Páginas")
            self.btn_toggle_borrar.setIcon(qta.icon('fa5s.edit'))
            self.btn_toggle_borrar.setProperty("estado", "normal")

        self.btn_toggle_borrar.style().unpolish(self.btn_toggle_borrar)
        self.btn_toggle_borrar.style().polish(self.btn_toggle_borrar)

        for i in range(self.grid_botones.count()):
            widget = self.grid_botones.itemAt(i).widget()
            if isinstance(widget, WebPAGE):
                widget.set_modo_eliminar(activado)

    def abrir_creador(self):
        if self.panel_creador.isHidden():
            self.panel_creador.show()
        else:
            self.panel_creador.cerrar_panel() 


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("ventanaPrincipal")
        self.setWindowTitle("Panel de control")
        self.resize(1024, 768)
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.stack = QStackedWidget()
        self.stack.setObjectName("stackPrincipal")
        self.setCentralWidget(self.stack)

        self.wallpapers_win = WallpaperConfiguratorWindow()
        self.music_win = MusicManager()
        self.monitor_win = MonitorSistema()

        self.menu = MenuPrincipal(
            ir_a_musica=lambda: self.mostrar(self.pagina_musica),
            ir_a_wallpapers=lambda: self.mostrar(self.pagina_wallpapers),
            ir_a_monitor=lambda: self.mostrar(self.pagina_monitor),
        )

        self.pagina_wallpapers = SeccionConVuelta(
            "Wallpapers",
            self.wallpapers_win.centralWidget(),
            volver_callback=lambda: self.mostrar(self.menu),
        )
        self.pagina_musica = SeccionConVuelta(
            "Música",
            self.music_win,
            volver_callback=lambda: self.mostrar(self.menu),
        )
        self.pagina_monitor = SeccionConVuelta(
            "Monitor de sistema",
            self.monitor_win.centralWidget(),
            volver_callback=lambda: self.mostrar(self.menu),
        )

        for pagina in (self.menu, self.pagina_wallpapers, self.pagina_musica, self.pagina_monitor):
            self.stack.addWidget(pagina)


        self.cargar_addons()

        self.mostrar(self.menu)

    def mostrar(self, pagina):
        self.stack.setCurrentWidget(pagina)


    def cargar_addons(self):
        carpeta_addons = "addons"
        
        if not os.path.exists(carpeta_addons):
            os.makedirs(carpeta_addons)
            return

        for archivo in os.listdir(carpeta_addons):
            if archivo.endswith(".py") and not archivo.startswith("__"):
                ruta_completa = os.path.join(carpeta_addons, archivo)
                nombre_modulo = archivo[:-3]

                try:
                    spec = importlib.util.spec_from_file_location(nombre_modulo, ruta_completa)
                    modulo = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(modulo)

                    if hasattr(modulo, "cargar_addon"):
                        nombre_addon, widget_addon = modulo.cargar_addon()

                        pagina_addon = SeccionConVuelta(
                            titulo=nombre_addon,
                            contenido=widget_addon,
                            volver_callback=lambda: self.mostrar(self.menu)
                        )
                        
                        self.stack.addWidget(pagina_addon)
                        self.menu.agregar_boton_addon(nombre_addon, lambda checked=False, p=pagina_addon: self.mostrar(p))
                        
                        print(f"✅ Addon cargado con éxito: {nombre_addon}")

                except Exception as e:
                    print(f"❌ Error al cargar el addon '{archivo}': {e}")
if __name__ == "__main__":
    app = QApplication(sys.argv)
    aplicar_tema_guardado_o_por_defecto()
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())