from __future__ import annotations

import os
os.environ["QT_API"] = "pyside6"
import qtawesome as qta

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QSplitter, QFrame, QSizePolicy, QDialog,
    QComboBox, QScrollArea, QGridLayout, QLineEdit, QStackedWidget
)

import backend.wallpaper_backend as theme_manager
from backend.wallpaper_backend import (
    ConfigManager, ProjectValidationError,
    detect_monitors, MonitorInfo, virtual_desktop_bounds,
    WallpaperEngineController,
    ImageLoader, ImageLoader_WE, ImageWorker
)

THUMB_SIZE = QSize(180, 101)


class MonitorTile(QPushButton):
    def __init__(self, monitor: MonitorInfo, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.setObjectName("monitorTile")
        self.setProperty("primary", "true" if monitor.is_primary else "false")
        self.setProperty("orientation", monitor.orientation)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel(f"Monitor {monitor.index}")
        title.setObjectName("monitorTileTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(f"{monitor.width}×{monitor.height}")
        subtitle.setObjectName("monitorTileSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        if monitor.is_primary:
            badge = QLabel("Principal")
            badge.setObjectName("monitorTileBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(badge)
        layout.addStretch()


class MonitorMapWidget(QWidget):
    monitor_selected = Signal(int)

    PADDING = 16
    MIN_TILE_PX = 90

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("monitorMap")
        self._monitors: list[MonitorInfo] = []
        self._tiles: list[MonitorTile] = []
        self.setMinimumHeight(220)

    def set_monitors(self, monitors: list[MonitorInfo]) -> None:
        for tile in self._tiles:
            tile.setParent(None)
            tile.deleteLater()
        self._tiles.clear()

        self._monitors = monitors
        for monitor in monitors:
            tile = MonitorTile(monitor, parent=self)
            tile.clicked.connect(lambda checked=False, m=monitor: self._on_tile_clicked(m))
            self._tiles.append(tile)
            
            tile.show() 
            
        self._relayout()

    def select_monitor(self, index: int) -> None:
        for tile in self._tiles:
            tile.setChecked(tile.monitor.index == index)

    def _on_tile_clicked(self, monitor: MonitorInfo) -> None:
        self.select_monitor(monitor.index)
        self.monitor_selected.emit(monitor.index)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        if not self._monitors:
            return

        min_x, min_y, max_x, max_y = virtual_desktop_bounds(self._monitors)
        desktop_w = max(max_x - min_x, 1)
        desktop_h = max(max_y - min_y, 1)

        available_w = max(self.width() - 2 * self.PADDING, 1)
        available_h = max(self.height() - 2 * self.PADDING, 1)

        scale = min(available_w / desktop_w, available_h / desktop_h)

        scaled_w = desktop_w * scale
        scaled_h = desktop_h * scale
        offset_x = self.PADDING + (available_w - scaled_w) / 2
        offset_y = self.PADDING + (available_h - scaled_h) / 2

        for tile in self._tiles:
            m = tile.monitor
            x = offset_x + (m.x - min_x) * scale
            y = offset_y + (m.y - min_y) * scale
            w = max(m.width * scale, self.MIN_TILE_PX)
            h = max(m.height * scale, self.MIN_TILE_PX)
            tile.setGeometry(int(x), int(y), int(w), int(h))

class SelectorTema(QWidget): 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("selectorTemaPanel")
        self.setFixedWidth(320) #

        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Carpeta de temas (.qss):"))
        
        self.picker_carpeta = FolderPicker("Elige la carpeta donde están tus temas...")
        carpeta_actual = theme_manager.obtener_carpeta_temas()
        self.picker_carpeta.set_path(str(carpeta_actual))
        self.picker_carpeta.folder_changed.connect(self._cambiar_carpeta)
        
        layout.addWidget(self.picker_carpeta)
        layout.addSpacing(10)

        layout.addWidget(QLabel("Tema a aplicar:"))
        self.combo = QComboBox()
        self.combo.setObjectName("comboTemas")
        layout.addWidget(self.combo)
        
        layout.addStretch() 

        botones = QHBoxLayout()
        
        btn_cerrar = QPushButton(" Cerrar")
        btn_cerrar.setIcon(qta.icon('fa5s.times'))
        btn_cerrar.setObjectName("btnCerrarSelectorTema")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; border-radius: 6px; }")
        btn_cerrar.clicked.connect(self.hide) 

        self.btn_aplicar = QPushButton(" Aplicar Tema")
        self.btn_aplicar.setIcon(qta.icon('fa5s.check'))
        self.btn_aplicar.setObjectName("btnAplicarTema")
        self.btn_aplicar.setCursor(Qt.PointingHandCursor)
        self.btn_aplicar.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; border-radius: 6px; }")
        self.btn_aplicar.clicked.connect(self._aplicar)

        botones.addWidget(btn_cerrar)
        botones.addWidget(self.btn_aplicar)
        layout.addLayout(botones)

        self._cargar_lista_temas()

    def _cambiar_carpeta(self, nueva_ruta: str) -> None:
        theme_manager.guardar_carpeta_temas(Path(nueva_ruta))
        self._cargar_lista_temas()

    def _cargar_lista_temas(self) -> None:
        self.combo.clear()
        self._temas = theme_manager.listar_temas()
        
        if not self._temas:
            self.combo.setEnabled(False)
            self.btn_aplicar.setEnabled(False)
            self.combo.addItem("No se encontró ningún archivo .qss")
            return
            
        self.combo.setEnabled(True)
        self.btn_aplicar.setEnabled(True)
        
        for ruta in self._temas:
            self.combo.addItem(ruta.stem, userData=str(ruta))

        tema_actual = theme_manager.obtener_tema_guardado()
        if tema_actual is not None:
            indice = self.combo.findData(str(tema_actual))
            if indice >= 0:
                self.combo.setCurrentIndex(indice)

    def _aplicar(self) -> None:
        ruta_str = self.combo.currentData()
        if not ruta_str:
            return
        ruta = Path(ruta_str)
        theme_manager.aplicar_tema(ruta)
        theme_manager.guardar_tema_preferido(ruta)

class FolderPicker(QWidget):
    folder_changed = Signal(str)

    def __init__(self, placeholder: str, parent=None):
        super().__init__(parent)
        self.setObjectName("folderPicker")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.path_field = QLineEdit()
        self.path_field.setObjectName("folderPathField")
        self.path_field.setPlaceholderText(placeholder)
        self.path_field.setReadOnly(False) 

        self.path_field.editingFinished.connect(self._on_manual_edit)

        self.browse_btn = QPushButton(" Elegir carpeta…")
        self.browse_btn.setIcon(qta.icon('fa5s.folder-open'))
        self.browse_btn.setObjectName("folderBrowseButton")
        self.browse_btn.clicked.connect(self._browse)

        layout.addWidget(self.path_field, 1)
        layout.addWidget(self.browse_btn)

    def _browse(self) -> None:
        ruta_inicial = self.path_field.text() if Path(self.path_field.text()).exists() else ""
        folder = QFileDialog.getExistingDirectory(self, "Selecciona una carpeta", ruta_inicial)
        if folder:
            self.set_path(folder)
            self.folder_changed.emit(folder)

    def _on_manual_edit(self) -> None:
        ruta = self.path_field.text().strip()
        if ruta and Path(ruta).exists():
            self.folder_changed.emit(ruta)

    def set_path(self, path: str) -> None:
        self.path_field.setText(path)

    def path(self) -> str:
        return self.path_field.text().strip()


class WallpaperGrid(QScrollArea):
    wallpaper_chosen = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("wallpaperGrid")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container.setObjectName("wallpaperGridContent")
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(10)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setWidget(self._container)

        self._buttons = []

    def clear(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons.clear()

    def add_thumbnail(self, worker: ImageWorker) -> None:
        btn = QPushButton()
        btn.setObjectName("wallpaperThumb")
        btn.setFixedSize(THUMB_SIZE)
        btn.setIcon(QPixmap.fromImage(worker.qimage))
        btn.setIconSize(THUMB_SIZE)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked=False, w=worker: self.wallpaper_chosen.emit(w))

        self._buttons.append(btn)
        self._reorganizar_grid()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reorganizar_grid()

    def _reorganizar_grid(self) -> None:
        if not self._buttons:
            return

        ancho_viewport = self.viewport().width()
        ancho_item = THUMB_SIZE.width() + self._grid.spacing()
        columnas = max(1, ancho_viewport // ancho_item)

        for i in reversed(range(self._grid.count())):
            self._grid.takeAt(i)

        for i, btn in enumerate(self._buttons):
            fila = i // columnas
            col = i % columnas
            self._grid.addWidget(btn, fila, col)


class WallpaperPanel(QWidget):
    wallpaper_applied = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("wallpaperPanel")

        self._monitor: MonitorInfo | None = None
        self._controller = None
        self._all_screens_provider = None

        self._image_loader: ImageLoader | None = None
        self._we_loader: ImageLoader_WE | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        self.header = QLabel("Selecciona un monitor")
        self.header.setObjectName("wallpaperPanelHeader")
        self.header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        root.addWidget(self.header)

        self.stack = QStackedWidget()
        self.stack.setObjectName("wallpaperStack")
        root.addWidget(self.stack, 1)


        images_view = QWidget()
        images_layout = QVBoxLayout(images_view)
        images_layout.setContentsMargins(0, 0, 0, 0)
        self.images_folder_picker = FolderPicker("Carpeta de imágenes para este monitor…")
        self.images_folder_picker.folder_changed.connect(self._on_images_folder_changed)
        self.images_grid = WallpaperGrid()
        self.images_grid.wallpaper_chosen.connect(self._on_wallpaper_chosen)
        images_layout.addWidget(self.images_folder_picker)
        images_layout.addWidget(self.images_grid, 1)
        self.stack.addWidget(images_view)


        we_view = QWidget()
        we_layout = QVBoxLayout(we_view)
        we_layout.setContentsMargins(0, 0, 0, 0)
        self.we_grid = WallpaperGrid()
        self.we_grid.wallpaper_chosen.connect(self._on_wallpaper_chosen)
        we_layout.addWidget(self.we_grid, 1)
        self.stack.addWidget(we_view)

        self.status_label = QLabel("")
        self.status_label.setObjectName("wallpaperPanelStatus")
        root.addWidget(self.status_label)

        self.setEnabled(False)

    def set_mode(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def bind(self, controller, all_screens_provider) -> None:
        self._controller = controller
        self._all_screens_provider = all_screens_provider

    def show_monitor(self, monitor: MonitorInfo, images_folder: str) -> None:
        self._monitor = monitor
        self.setEnabled(True)
        self.header.setText(f"Monitor {monitor.index} · {monitor.width}×{monitor.height} · {monitor.orientation}")
        self.status_label.setText("")

        self.images_folder_picker.set_path(images_folder or "")
        self._reload_images_tab()
        self._reload_we_tab()

    def _reload_images_tab(self) -> None:
        self.images_grid.clear()
        self._stop_loader(self._image_loader)
        folder = self.images_folder_picker.path()
        if not folder or self._controller is None: return

        self._image_loader = ImageLoader(folder, THUMB_SIZE, self._controller.apply_wallpaper)
        self._image_loader.image_loaded.connect(self.images_grid.add_thumbnail)
        self._image_loader.start()

    def _reload_we_tab(self) -> None:
        self.we_grid.clear()
        self._stop_loader(self._we_loader)

        folder = self._controller.config_manager.data.get("we_content_folder", "")
        if not folder or self._controller is None or self._monitor is None: return

        self._we_loader = ImageLoader_WE(
            folder,
            THUMB_SIZE,
            self._monitor.orientation,
            self._controller.get_data_we,
            self._controller.apply_wallpaper_engine,
        )
        self._we_loader.image_loaded.connect(self.we_grid.add_thumbnail)
        self._we_loader.start()

    @staticmethod
    def _stop_loader(loader) -> None:
        if loader is not None and loader.isRunning():
            loader.stop()
            loader.wait()

    def _on_images_folder_changed(self, folder: str) -> None:
        if self._monitor is not None and self._controller is not None:
            self._controller.config_manager.set_monitor_field(self._monitor.index, "wallpaper_folder", folder)
            self._controller.config_manager.save()
        self._reload_images_tab()

    def _on_wallpaper_chosen(self, worker: ImageWorker) -> None:
        if self._monitor is None or self._controller is None: return
        monitor_id = self._monitor.index
        if worker.kind == "static":
            screens = self._all_screens_provider() if self._all_screens_provider else []
            self._controller.apply_wallpaper(worker.path, monitor_id, screens)
        else:
            self._controller.apply_wallpaper_engine(worker.path, monitor_id)
        self.status_label.setText(f"Wallpaper aplicado al Monitor {monitor_id}.")
        self.wallpaper_applied.emit(monitor_id)

class TopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        self.status_label = QLabel("Modo: standalone (sin proyecto YASB vinculado)")
        self.status_label.setObjectName("projectStatusLabel")

 
        self.btn_ajustes = QPushButton(" Ajustes")
        self.btn_ajustes.setIcon(qta.icon('fa5s.cog'))
        self.btn_ajustes.setObjectName("settingsButton")
        self.btn_ajustes.setCursor(Qt.CursorShape.PointingHandCursor)

        self.link_btn = QPushButton(" Seleccionar carpeta del proyecto YASB…")
        self.link_btn.setIcon(qta.icon('fa5s.link'))
        self.link_btn.setObjectName("linkProjectButton")

        self.unlink_btn = QPushButton(" Desvincular")
        self.unlink_btn.setIcon(qta.icon('fa5s.unlink'))
        self.unlink_btn.setObjectName("unlinkProjectButton")
        self.unlink_btn.setVisible(False)

        layout.addWidget(self.status_label, 1)
        layout.addWidget(self.btn_ajustes) 
        layout.addWidget(self.link_btn)
        layout.addWidget(self.unlink_btn)
        
class ConfiguracionGeneralDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("configGeneralDialog")
        self.setWindowTitle("Configuración General (Standalone)")
        self.resize(600, 200)
        self.config_manager = config_manager
        
        layout = QVBoxLayout(self)

        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("Steam API Key:"))
        self.api_input = QLineEdit()
        self.api_input.setObjectName("apiInput")
        self.api_input.setText(self.config_manager.data.get("STEAM_API_KEY", ""))
        self.api_input.setPlaceholderText("Pega aquí tu clave de la API de Steam...")
        api_layout.addWidget(self.api_input)
        layout.addLayout(api_layout)


        exe_layout = QHBoxLayout()
        exe_layout.addWidget(QLabel("Ruta we_exe:"))
        self.exe_input = QLineEdit()
        self.exe_input.setObjectName("exeInput")
        self.exe_input.setPlaceholderText(r"Ej: C:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\wallpaper32.exe")
        self.exe_input.setText(self.config_manager.data.get("we_exe", ""))
        btn_buscar_exe = QPushButton(" Buscar...")
        btn_buscar_exe.setObjectName("btnBuscarExe")
        btn_buscar_exe.setIcon(qta.icon('fa5s.search'))
        btn_buscar_exe.clicked.connect(self._buscar_exe)
        exe_layout.addWidget(self.exe_input)
        exe_layout.addWidget(btn_buscar_exe)
        layout.addLayout(exe_layout)

        we_folder_layout = QHBoxLayout()
        we_folder_layout.addWidget(QLabel("Carpeta Workshop WE:"))
        self.we_folder_input = QLineEdit()
        self.we_folder_input.setObjectName("weFolderInput")
        self.we_folder_input.setPlaceholderText(r"Ej: C:\Program Files (x86)\Steam\steamapps\workshop\content\431960")
        self.we_folder_input.setText(self.config_manager.data.get("we_content_folder", ""))
        btn_buscar_we = QPushButton(" Buscar...")
        btn_buscar_we.setObjectName("btnBuscarWe")
        btn_buscar_we.setIcon(qta.icon('fa5s.search'))
        btn_buscar_we.clicked.connect(self._buscar_we_folder)
        we_folder_layout.addWidget(self.we_folder_input)
        we_folder_layout.addWidget(btn_buscar_we)
        layout.addLayout(we_folder_layout)


        botones_layout = QHBoxLayout()
        btn_guardar = QPushButton(" Guardar")
        btn_guardar.setObjectName("btnGuardarConfig")
        btn_guardar.setIcon(qta.icon('fa5s.save'))
        btn_guardar.clicked.connect(self._guardar_configuracion)
        btn_cancelar = QPushButton(" Cancelar")
        btn_cancelar.setObjectName("btnCancelarConfig")
        btn_cancelar.setIcon(qta.icon('fa5s.times'))
        btn_cancelar.clicked.connect(self.reject)
        botones_layout.addStretch()
        botones_layout.addWidget(btn_guardar)
        botones_layout.addWidget(btn_cancelar)
        layout.addLayout(botones_layout)

    def _buscar_exe(self) -> None:
        ruta_defecto = r"C:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine"
        if not Path(ruta_defecto).exists(): ruta_defecto = "" 
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar ejecutable de Wallpaper Engine", ruta_defecto, "Ejecutables (*.exe)")
        if ruta: self.exe_input.setText(Path(ruta).as_posix())

    def _buscar_we_folder(self) -> None:
        ruta_defecto = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960"
        if not Path(ruta_defecto).exists(): ruta_defecto = ""
        ruta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de la Workshop (431960)", ruta_defecto)
        if ruta: self.we_folder_input.setText(Path(ruta).as_posix())

    def _guardar_configuracion(self) -> None:
        self.config_manager.data["STEAM_API_KEY"] = self.api_input.text().strip()
        self.config_manager.data["we_exe"] = self.exe_input.text().strip()
        self.config_manager.data["we_content_folder"] = self.we_folder_input.text().strip()
        self.config_manager.save()
        self.accept()

class WallpaperConfiguratorWindow(QMainWindow):
    def __init__(self, project_dir: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("wallpaperConfiguratorWindow")
        self.setWindowTitle("Configurador de Wallpapers · YASB")
        self.resize(1100, 680)

        self.config_manager = ConfigManager()
        self.controller = WallpaperEngineController(self.config_manager)
        self._monitors = []

        self._build_ui()
        self._connect_signals()

        from PySide6.QtCore import QSettings
        settings = QSettings("EstebanApps", "PanelDeControl")
        saved_project = settings.value("yasb/project_path", "")


        ruta_a_cargar = project_dir if project_dir else saved_project

        if ruta_a_cargar and Path(ruta_a_cargar).exists():
            self._link_project(str(ruta_a_cargar))
        else:
            self.config_manager.load()
            
        self.refresh_monitors()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_bar = TopBar()
        root.addWidget(self.top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        self.monitor_map = MonitorMapWidget()
        left_layout.addWidget(self.monitor_map, 1)

        self.mode_layout = QHBoxLayout()
        self.btn_modo_img = QPushButton(" Imágenes")
        self.btn_modo_img.setObjectName("btnModoImg")
        self.btn_modo_img.setIcon(qta.icon('fa5s.image'))
        self.btn_modo_we = QPushButton(" Wallpaper Engine")
        self.btn_modo_we.setObjectName("btnModoWe")
        self.btn_modo_we.setIcon(qta.icon('fa5s.cogs'))

        estilo_toggle = """
            QPushButton {
                padding: 12px; border-radius: 6px; font-weight: bold;
            }
        """
        for btn in (self.btn_modo_img, self.btn_modo_we):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(estilo_toggle)

        self.btn_modo_img.setChecked(True)

        self.mode_layout.addWidget(self.btn_modo_img)
        self.mode_layout.addWidget(self.btn_modo_we)
        left_layout.addLayout(self.mode_layout)

        splitter.addWidget(left_col)

        self.wallpaper_panel = WallpaperPanel()
        self.wallpaper_panel.bind(self.controller, self._current_screens)
        splitter.addWidget(self.wallpaper_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter, 1)

    def _connect_signals(self) -> None:

        self.top_bar.btn_ajustes.clicked.connect(self._abrir_ajustes)
        
        self.top_bar.link_btn.clicked.connect(self._on_link_clicked)
        self.top_bar.unlink_btn.clicked.connect(self._on_unlink_clicked)
        self.monitor_map.monitor_selected.connect(self._on_monitor_selected)

        self.btn_modo_img.clicked.connect(lambda: self._cambiar_modo(0))
        self.btn_modo_we.clicked.connect(lambda: self._cambiar_modo(1))

    def _abrir_ajustes(self) -> None:
        dialogo = ConfiguracionGeneralDialog(self.config_manager, self)
        dialogo.exec()

    def _cambiar_modo(self, index: int) -> None:
        self.btn_modo_img.setChecked(index == 0)
        self.btn_modo_we.setChecked(index == 1)
        self.wallpaper_panel.set_mode(index)

    def refresh_monitors(self) -> None:
        self._monitors = detect_monitors()
        self.config_manager.sync_monitor_count(len(self._monitors))
        self.config_manager.save()
        self.monitor_map.set_monitors(self._monitors)

    @staticmethod
    def _current_screens():
        app = QGuiApplication.instance()
        return list(app.screens()) if app else []

    def _on_monitor_selected(self, index: int) -> None:
        monitor = next((m for m in self._monitors if m.index == index), None)
        if monitor is None:
            return

        entry = self.config_manager.get_monitor_entry(index)
        images_folder = entry.get("wallpaper_folder", "")
        
        self.wallpaper_panel.show_monitor(monitor, images_folder)

    def _on_link_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Selecciona la carpeta del proyecto YASB (yasb-multiple-monitor-wallpaper...)"
        )
        if folder:
            self._link_project(folder)

    def _link_project(self, folder: str) -> None:
        try:
            self.config_manager.link_project(folder)
        except ProjectValidationError as exc:
            QMessageBox.warning(self, "Proyecto inválido", str(exc))
            return


        from PySide6.QtCore import QSettings
        settings = QSettings("EstebanApps", "PanelDeControl")
        settings.setValue("yasb/project_path", folder)

        self.top_bar.status_label.setText(f"Vinculado a: {folder}")
        self.top_bar.unlink_btn.setVisible(True)
        self.refresh_monitors()

    def _on_unlink_clicked(self) -> None:

        from PySide6.QtCore import QSettings
        settings = QSettings("EstebanApps", "PanelDeControl")
        settings.remove("yasb/project_path")

        self.config_manager.unlink_project()
        self.top_bar.status_label.setText("Modo: standalone (sin proyecto YASB vinculado)")
        self.top_bar.unlink_btn.setVisible(False)
        

        self.wallpaper_panel.setEnabled(False)
        self.wallpaper_panel.header.setText("Selecciona un monitor")
        self.wallpaper_panel.status_label.setText("")
        self.wallpaper_panel.images_folder_picker.set_path("")
        self.wallpaper_panel.images_grid.clear()
        self.wallpaper_panel.we_grid.clear()

        self.refresh_monitors()