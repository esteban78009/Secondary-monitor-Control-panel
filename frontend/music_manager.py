import os
import sys

# Forzar a qtawesome/qtpy a usar PySide6
os.environ["QT_API"] = "pyside6"
import qtawesome as qta

import random
from backend.music_manager_backend import * 
from PySide6.QtCore import QThread, Signal, Qt, QUrl, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QScrollArea, QLabel, QHBoxLayout,
    QStackedWidget, QLineEdit, QComboBox, QGridLayout, 
    QFileDialog, QFrame, QSlider, QStyle, QMenu
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

class MusicManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("musicManagerCentralWidget")
        self.resize(1024, 768)
        

        self.slider_volumen = QSlider(Qt.Horizontal)
        self.slider_volumen.setObjectName("sliderVolumen")
        self.slider_volumen.setRange(0, 100)
        self.slider_volumen.setValue(50) 
        self.slider_volumen.setFixedWidth(120) 
        self.slider_volumen.valueChanged.connect(self.cambiar_volumen)
        self.shuffle_activado = False

        self.playlist = []
        self.lista_widgets_canciones = [] 
        self.current_index = -1
        self.current_playlist_list = []
        self.editing_playlist_songs = []
        self.current_playback_list = []

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)
        
        self.player.positionChanged.connect(self.actualizar_slider)
        self.player.durationChanged.connect(self.actualizar_rango_slider)
        self.player.playbackStateChanged.connect(self.actualizar_boton_play)
        self.player.mediaStatusChanged.connect(self.verificar_fin_cancion)

        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(5, 5, 5, 5)


        self.sidebar_expanded = True
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("sidebarWidget")
        self.sidebar_widget.setFixedWidth(160)
        
        layout_sidebar = QVBoxLayout(self.sidebar_widget)
        layout_sidebar.setContentsMargins(0, 0, 0, 0)
        layout_sidebar.setAlignment(Qt.AlignTop)
        
        self.btn_menu = QPushButton(" Menú")
        self.btn_menu.setObjectName("btnMenuPrincipal")
        self.btn_menu.setIcon(qta.icon('fa5s.bars'))
        self.btn_menu.clicked.connect(self.toggle_sidebar)
        layout_sidebar.addWidget(self.btn_menu)

        self.btn_nav_musica = QPushButton(" Música")
        self.btn_nav_musica.setObjectName("btnNavMusica")
        self.btn_nav_musica.setIcon(qta.icon('fa5s.music'))
        
        self.btn_nav_playlists = QPushButton(" Playlists")
        self.btn_nav_playlists.setObjectName("btnNavPlaylists")
        self.btn_nav_playlists.setIcon(qta.icon('fa5s.folder'))
        
        self.btn_nav_artistas = QPushButton(" Artistas")
        self.btn_nav_artistas.setObjectName("btnNavArtistas")
        self.btn_nav_artistas.setIcon(qta.icon('fa5s.user'))
        
        self.btn_nav_generos = QPushButton(" Géneros")
        self.btn_nav_generos.setObjectName("btnNavGeneros")
        self.btn_nav_generos.setIcon(qta.icon('fa5s.tag'))
        
        self.btn_nav_crear = QPushButton(" Crear Playlist")
        self.btn_nav_crear.setObjectName("btnNavCrear")
        self.btn_nav_crear.setIcon(qta.icon('fa5s.tools'))

        for btn_nav in (self.btn_menu, self.btn_nav_musica, self.btn_nav_playlists,
                        self.btn_nav_artistas, self.btn_nav_generos, self.btn_nav_crear):
            btn_nav.setCursor(Qt.PointingHandCursor)
            
        self.btn_nav_musica.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.btn_nav_playlists.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.btn_nav_artistas.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.btn_nav_generos.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        self.btn_nav_crear.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(4))

        layout_sidebar.addWidget(self.btn_nav_musica)
        layout_sidebar.addWidget(self.btn_nav_playlists)
        layout_sidebar.addWidget(self.btn_nav_artistas)
        layout_sidebar.addWidget(self.btn_nav_generos)
        layout_sidebar.addWidget(self.btn_nav_crear)

        layout_principal.addWidget(self.sidebar_widget)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("stackedWidgetMusic")
        self.stacked_widget.currentChanged.connect(self.on_page_changed)

        self.page_musica = QWidget()
        layout_izquierdo = QVBoxLayout(self.page_musica) 

        self.btn_cambiar_carpeta = QPushButton(" Elegir Nueva Carpeta de Música")
        self.btn_cambiar_carpeta.setObjectName("btnCambiarCarpeta")
        self.btn_cambiar_carpeta.setIcon(qta.icon('fa5s.folder-open'))
        self.btn_cambiar_carpeta.setCursor(Qt.PointingHandCursor)
        self.btn_cambiar_carpeta.setStyleSheet("""
            QPushButton { 
                text-align: center; padding: 12px; 
                font-size: 14px; font-weight: bold; border-radius: 8px;
                border: 1px solid; margin-bottom: 10px;
            }
        """)
        self.btn_cambiar_carpeta.clicked.connect(self.seleccionar_nueva_carpeta)
        layout_izquierdo.addWidget(self.btn_cambiar_carpeta)

        self.scroll_area, self.contenedor_lista, self.layout_lista = self._crear_area_scroll()
        layout_izquierdo.addWidget(self.scroll_area)

        self.label_seleccion = QLabel("no hay cancion seleccionada") 
        self.label_seleccion.setObjectName("labelSeleccionActual")
        self.label_seleccion.setWordWrap(True)
        layout_izquierdo.addWidget(self.label_seleccion)
        
        self.stacked_widget.addWidget(self.page_musica)
        
    
        ruta_guardada = cargar_configuracion()
        ruta_musica = ruta_guardada if ruta_guardada and os.path.exists(ruta_guardada) else ""

        self.page_playlists = QWidget()
        layout_pl = QHBoxLayout(self.page_playlists)
        col_izq_pl = QVBoxLayout()
        
        header_pl = QHBoxLayout()
        lbl_titulo_pl = QLabel("MIS PLAYLISTS")
        lbl_titulo_pl.setObjectName("lblTituloPl")
        lbl_titulo_pl.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.btn_toggle_borrar_pl = QPushButton(" Editar")
        self.btn_toggle_borrar_pl.setObjectName("btnToggleBorrarPl")
        self.btn_toggle_borrar_pl.setIcon(qta.icon('fa5s.edit'))
        self.btn_toggle_borrar_pl.setCheckable(True)
        self.btn_toggle_borrar_pl.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_borrar_pl.setProperty("estado", "normal") 
        self.btn_toggle_borrar_pl.setStyleSheet("""
            QPushButton { padding: 6px 12px; border-radius: 6px; border: 1px solid; font-weight: bold; }
        """)
        self.btn_toggle_borrar_pl.clicked.connect(self.toggle_edicion_playlists)
        
        header_pl.addWidget(lbl_titulo_pl)
        header_pl.addStretch()
        header_pl.addWidget(self.btn_toggle_borrar_pl)
        col_izq_pl.addLayout(header_pl)
        
        self.scroll_pl_list, self.widget_pl_list, self.layout_pl_list = self._crear_area_scroll()
        col_izq_pl.addWidget(self.scroll_pl_list)
        
        self.scroll_pl_songs, self.widget_pl_songs, self.layout_pl_songs = self._crear_area_scroll()
        
        layout_pl.addLayout(col_izq_pl, stretch=1)
        layout_pl.addWidget(self.scroll_pl_songs, stretch=1)
        self.stacked_widget.addWidget(self.page_playlists)
        
        self.botones_eliminar_pl = []

        self.page_artistas = QWidget()
        layout_artistas = QHBoxLayout(self.page_artistas)
        
        self.scroll_artistas_list, self.widget_artistas_list, self.layout_artistas_list = self._crear_area_scroll()
        self.scroll_artistas_songs, self.widget_artistas_songs, self.layout_artistas_songs = self._crear_area_scroll()

        layout_artistas.addWidget(self.scroll_artistas_list, stretch=1)
        layout_artistas.addWidget(self.scroll_artistas_songs, stretch=1)
        self.stacked_widget.addWidget(self.page_artistas)


        self.page_generos = QWidget()
        layout_generos = QHBoxLayout(self.page_generos)

        col_izq_gen = QVBoxLayout()
        lbl_titulo_gen = QLabel("GÉNEROS")
        lbl_titulo_gen.setObjectName("lblTituloGen")
        lbl_titulo_gen.setAlignment(Qt.AlignCenter)
        lbl_titulo_gen.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        col_izq_gen.addWidget(lbl_titulo_gen)
        
        self.scroll_generos_list, self.widget_generos_list, self.layout_generos_list = self._crear_area_scroll()
        self.layout_generos_list.setSpacing(2) 
        col_izq_gen.addWidget(self.scroll_generos_list) 
        
        col_der_gen = QVBoxLayout()
        lbl_titulo_songs = QLabel("CANCIONES")
        lbl_titulo_songs.setObjectName("lblTituloSongs")
        lbl_titulo_songs.setAlignment(Qt.AlignCenter)
        lbl_titulo_songs.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        col_der_gen.addWidget(lbl_titulo_songs)

        self.lbl_generos_estado = QLabel("Selecciona un género para ver sus canciones")
        self.lbl_generos_estado.setObjectName("lblGenerosEstado")
        self.lbl_generos_estado.setAlignment(Qt.AlignCenter)
        self.lbl_generos_estado.setWordWrap(True)
        self.lbl_generos_estado.setStyleSheet("font-size: 13px; padding: 10px;")
        col_der_gen.addWidget(self.lbl_generos_estado)
        
        self.scroll_generos_songs, self.widget_generos_songs, self.layout_generos_songs = self._crear_area_scroll()
        col_der_gen.addWidget(self.scroll_generos_songs) 

        layout_generos.addLayout(col_izq_gen, stretch=2) 
        layout_generos.addLayout(col_der_gen, stretch=3) 
        self.stacked_widget.addWidget(self.page_generos)
        
        self.botones_generos = {}
        self.genero_actual = None

        self.page_crear = QWidget()
        layout_crear = QVBoxLayout(self.page_crear)
        
        panel_controles = QFrame()
        panel_controles.setObjectName("panelControlesCrear")
        panel_controles.setStyleSheet("""
            QFrame { border: 1px solid; border-radius: 10px; }
            QLabel { font-weight: bold; font-size: 13px; }
        """)
        layout_panel = QVBoxLayout(panel_controles)
        layout_panel.setContentsMargins(15, 15, 15, 15)
        layout_panel.setSpacing(15)

        fila_superior = QHBoxLayout()
        fila_inferior = QHBoxLayout()
        
        estilo_inputs = """
            QComboBox, QLineEdit {
                border: 1px solid; border-radius: 6px;
                padding: 10px; font-size: 13px;
            }
        """

        self.cb_playlist_editar = QComboBox() 
        self.cb_playlist_editar.setObjectName("cbPlaylistEditar")
        self.cb_playlist_editar.setStyleSheet(estilo_inputs)
        self.cb_playlist_editar.currentIndexChanged.connect(self.cargar_playlist_en_editor)
        
        self.cb_filtrar_genero = QComboBox()
        self.cb_filtrar_genero.setObjectName("cbFiltrarGenero")
        self.cb_filtrar_genero.setStyleSheet(estilo_inputs)
        self.cb_filtrar_genero.currentIndexChanged.connect(self.actualizar_listas_editor)

        self.txt_playlist_nombre = QLineEdit() 
        self.txt_playlist_nombre.setObjectName("txtPlaylistNombre")
        self.txt_playlist_nombre.setStyleSheet(estilo_inputs)
        self.txt_playlist_nombre.setPlaceholderText("Escribe un nombre para tu playlist...")
        
        self.btn_guardar_playlist = QPushButton(" Guardar")
        self.btn_guardar_playlist.setIcon(qta.icon('fa5s.save'))
        self.btn_guardar_playlist.setCursor(Qt.PointingHandCursor)
        self.btn_guardar_playlist.setObjectName("btnGuardarPlaylist")
        self.btn_guardar_playlist.setStyleSheet("padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_guardar_playlist.clicked.connect(self.guardar_playlist_actual)

        self.btn_eliminar_playlist = QPushButton(" Eliminar")
        self.btn_eliminar_playlist.setIcon(qta.icon('fa5s.times'))
        self.btn_eliminar_playlist.setCursor(Qt.PointingHandCursor)
        self.btn_eliminar_playlist.setObjectName("btnEliminarPlaylist")
        self.btn_eliminar_playlist.setStyleSheet("padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        self.btn_eliminar_playlist.clicked.connect(self.eliminar_playlist_actual)

        fila_superior.addWidget(QLabel("Cargar:"))
        fila_superior.addWidget(self.cb_playlist_editar, stretch=2)
        fila_superior.addSpacing(20)
        fila_superior.addWidget(QLabel("Filtrar Género:"))
        fila_superior.addWidget(self.cb_filtrar_genero, stretch=2)

        fila_inferior.addWidget(QLabel("Nombre:"))
        fila_inferior.addWidget(self.txt_playlist_nombre, stretch=3)
        fila_inferior.addSpacing(20)
        fila_inferior.addWidget(self.btn_guardar_playlist)
        fila_inferior.addWidget(self.btn_eliminar_playlist)

        layout_panel.addLayout(fila_superior)
        layout_panel.addLayout(fila_inferior)
        layout_crear.addWidget(panel_controles)
        layout_crear.addSpacing(10)

        layout_columnas_crear = QHBoxLayout()
        layout_col_izq = QVBoxLayout()
        layout_col_izq.addWidget(QLabel("Disponibles (Toca para añadir):"))
        
        self.scroll_disponibles, self.widget_disponibles, self.layout_disponibles = self._crear_area_scroll(ocultar_vertical=True)
        self.layout_disponibles.setSpacing(2) 
        layout_col_izq.addWidget(self.scroll_disponibles)
        
        layout_col_der = QVBoxLayout()
        layout_col_der.addWidget(QLabel("Añadidas (Toca para quitar):"))
        
        self.scroll_actuales, self.widget_actuales, self.layout_actuales = self._crear_area_scroll(ocultar_vertical=True)
        self.layout_actuales.setSpacing(2) 
        layout_col_der.addWidget(self.scroll_actuales)

        layout_columnas_crear.addLayout(layout_col_izq, stretch=1)
        layout_columnas_crear.addLayout(layout_col_der, stretch=1)
        layout_crear.addLayout(layout_columnas_crear)
        
        self.stacked_widget.addWidget(self.page_crear)
        layout_principal.addWidget(self.stacked_widget, stretch=2)

        if ruta_musica:
            self.hilo = EscaneoMusica(ruta_musica)
            self.hilo.cancion.connect(self.agregar_cancion)
            self.hilo.start()
        else:
            self.label_seleccion.setText("Por favor, elige una carpeta de música usando el botón superior.")

        # --- PANEL DERECHO ---
        self.panel_derecho = QWidget()
        self.panel_derecho.setObjectName("panelDerechoPlayer")
        layout_derecho = QVBoxLayout(self.panel_derecho)
        
        # Filtro de Búsqueda arriba de la carátula
        self.txt_buscar_musica = QLineEdit()
        self.txt_buscar_musica.setObjectName("txtBuscarMusica")
        self.txt_buscar_musica.setPlaceholderText("Buscar canción o artista...")
        self.txt_buscar_musica.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                font-size: 14px;
                border: 1px solid;
                border-radius: 8px;
            }
        """)
        self.txt_buscar_musica.textChanged.connect(self.filtrar_musica)
        layout_derecho.addWidget(self.txt_buscar_musica)
        layout_derecho.addSpacing(15)

        self.lbl_caratula = QLabel("sin reproduccion actual")
        self.lbl_caratula.setObjectName("lblCaratulaPlayer")
        self.lbl_caratula.setAlignment(Qt.AlignCenter)
        self.lbl_caratula.setFixedSize(250, 250)
        self.lbl_caratula.setStyleSheet("""
            border: 2px dashed; 
            border-radius: 12px; 
            font-size: 14px;
        """)
        
        self.lbl_info_derecha = QLabel("")
        self.lbl_info_derecha.setObjectName("lblInfoDerecha")
        self.lbl_info_derecha.setAlignment(Qt.AlignCenter)
        self.lbl_info_derecha.setWordWrap(True)
        
        self.lbl_tiempo_actual = QLabel("00:00")
        self.lbl_tiempo_total = QLabel("00:00")
        
        self.slider_tiempo = QSlider(Qt.Horizontal)
        self.slider_tiempo.setObjectName("sliderTiempo")
        self.slider_tiempo.setEnabled(False)
        self.slider_tiempo.sliderMoved.connect(self.cambiar_posicion_audio)

        layout_slider_tiempo = QHBoxLayout()
        layout_slider_tiempo.addWidget(self.lbl_tiempo_actual)
        layout_slider_tiempo.addWidget(self.slider_tiempo)
        layout_slider_tiempo.addWidget(self.lbl_tiempo_total)

        layout_controles = QHBoxLayout()
        icono_prev = self.style().standardIcon(QStyle.SP_MediaSkipBackward)
        icono_play = self.style().standardIcon(QStyle.SP_MediaPlay)
        icono_next = self.style().standardIcon(QStyle.SP_MediaSkipForward)
        
        self.btn_prev = QPushButton(icono_prev, "")
        self.btn_prev.setObjectName("btnPrevTrack")
        self.btn_play = QPushButton(icono_play, "")
        self.btn_play.setObjectName("btnPlayTrack")
        self.btn_next = QPushButton(icono_next, "")
        self.btn_next.setObjectName("btnNextTrack")

        self.btn_shuffle = QPushButton("") 
        self.btn_shuffle.setObjectName("btnShuffleTrack")
        self.btn_shuffle.setIcon(qta.icon('fa5s.random'))
        self.btn_shuffle.setCheckable(True) 
        self.btn_shuffle.setProperty("estado", "inactivo") 
        self.btn_shuffle.clicked.connect(self.toggle_shuffle) 

        # Botón "+" movido aquí
        self.btn_add_playlist = QPushButton("")
        self.btn_add_playlist.setObjectName("btnAddPlaylistTrack")
        self.btn_add_playlist.setIcon(qta.icon('fa5s.plus'))
        self.btn_add_playlist.setToolTip("Añadir canción actual a una Playlist")
        self.btn_add_playlist.clicked.connect(self.mostrar_menu_playlists_player)

        tam_icono = QSize(28, 28)
        tam_boton = QSize(55, 55)
        
        for btn in [self.btn_prev, self.btn_play, self.btn_next, self.btn_shuffle, self.btn_add_playlist]:
            btn.setIconSize(tam_icono)
            btn.setFixedSize(tam_boton)
            btn.setCursor(Qt.PointingHandCursor)

        self.btn_prev.setEnabled(False)
        self.btn_play.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_add_playlist.setEnabled(False) # Se activa al reproducir

        self.btn_play.clicked.connect(self.toggle_reproduccion)
        self.btn_prev.clicked.connect(self.cancion_anterior)
        self.btn_next.clicked.connect(self.cancion_siguiente)

        layout_botones = QHBoxLayout()
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_prev)
        layout_botones.addWidget(self.btn_play)
        layout_botones.addWidget(self.btn_next)
        layout_botones.addWidget(self.btn_shuffle) 
        layout_botones.addWidget(self.btn_add_playlist) 
        layout_botones.addStretch() 

        layout_volumen = QHBoxLayout()
        layout_volumen.addStretch()
        layout_volumen.addWidget(QLabel("Volumen: "))
        layout_volumen.addWidget(self.slider_volumen)
        layout_volumen.addStretch()

        layout_derecho.addWidget(self.lbl_caratula, alignment=Qt.AlignCenter)
        layout_derecho.addWidget(self.lbl_info_derecha, alignment=Qt.AlignCenter)
        layout_derecho.addSpacing(30) 
        
        layout_derecho.addLayout(layout_slider_tiempo)
        layout_derecho.addLayout(layout_botones)
        layout_derecho.addLayout(layout_volumen)
        layout_derecho.addStretch(1) 

        layout_principal.addWidget(self.panel_derecho, stretch=1)

    def _crear_area_scroll(self, ocultar_vertical=False):
        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        if ocultar_vertical:
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(widget)
        return scroll, widget, layout

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar_widget.setFixedWidth(50)
            self.btn_menu.setText("")
            self.btn_nav_musica.setText("")
            self.btn_nav_playlists.setText("")
            self.btn_nav_artistas.setText("")
            self.btn_nav_generos.setText("")
            self.btn_nav_crear.setText("")
            self.sidebar_expanded = False
        else:
            self.sidebar_widget.setFixedWidth(160)
            self.btn_menu.setText(" Menú")
            self.btn_nav_musica.setText(" Música")
            self.btn_nav_playlists.setText(" Playlists")
            self.btn_nav_artistas.setText(" Artistas")
            self.btn_nav_generos.setText(" Géneros")
            self.btn_nav_crear.setText(" Crear Playlist")
            self.sidebar_expanded = True

    def on_page_changed(self, index):
        if index == 1:
            self.actualizar_vista_playlists()
        elif index == 2:
            self.actualizar_vista_artistas()
        elif index == 3:
            self.actualizar_vista_generos()
        elif index == 4:
            self.actualizar_vista_crear()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())
                    child.layout().deleteLater()

    def actualizar_vista_playlists(self):
        if hasattr(self, 'btn_toggle_borrar_pl') and self.btn_toggle_borrar_pl.isChecked():
            self.btn_toggle_borrar_pl.setChecked(False)
            self.toggle_edicion_playlists(False)

        self.clear_layout(self.layout_pl_list)
        self.clear_layout(self.layout_pl_songs)
        self.botones_eliminar_pl = [] 
        
        nombres = obtener_nombres_playlists()
        for nombre_pl in nombres:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)

            btn_pl = QPushButton(f" {nombre_pl}")
            btn_pl.setObjectName("btnPlaylistList")
            btn_pl.setIcon(qta.icon('fa5s.folder'))
            btn_pl.setStyleSheet("""
                QPushButton { text-align: left; padding: 12px; font-size: 14px; border-radius: 6px; border: 1px solid; }
            """)
            btn_pl.setCursor(Qt.PointingHandCursor)
            btn_pl.clicked.connect(lambda checked=False, n=nombre_pl: self.cargar_canciones_playlist(n))
            
            btn_del = QPushButton("")
            btn_del.setObjectName("btnDeletePlaylist")
            btn_del.setIcon(qta.icon('fa5s.trash'))
            btn_del.setFixedWidth(40)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet("QPushButton { border-radius: 6px; }")
            btn_del.clicked.connect(lambda checked=False, n=nombre_pl: self.eliminar_playlist_desde_lista(n))
            btn_del.hide() 

            self.botones_eliminar_pl.append(btn_del) 

            row_layout.addWidget(btn_pl)
            row_layout.addWidget(btn_del)
            self.layout_pl_list.addLayout(row_layout)

    def toggle_edicion_playlists(self, activado):
        if activado:
            self.btn_toggle_borrar_pl.setText(" Terminar")
            self.btn_toggle_borrar_pl.setIcon(qta.icon('fa5s.check'))
            self.btn_toggle_borrar_pl.setProperty("estado", "editando")
        else:
            self.btn_toggle_borrar_pl.setText(" Editar")
            self.btn_toggle_borrar_pl.setIcon(qta.icon('fa5s.edit'))
            self.btn_toggle_borrar_pl.setProperty("estado", "normal")

        self.btn_toggle_borrar_pl.style().unpolish(self.btn_toggle_borrar_pl)
        self.btn_toggle_borrar_pl.style().polish(self.btn_toggle_borrar_pl)

        for btn in self.botones_eliminar_pl:
            btn.setVisible(activado)

    def cargar_canciones_playlist(self, nombre_pl):
        self.clear_layout(self.layout_pl_songs)
        rutas_canciones = cargar_playlist(nombre_pl) 
        playlist_actual_songs = []
        
        for ruta in rutas_canciones:
            for song in self.playlist:
                if song.musica == ruta:
                    playlist_actual_songs.append(song)
                    break

        for i, cancion in enumerate(playlist_actual_songs):
            minutos, segundos = cancion.duracion
            btn_song = QPushButton(f"{cancion.artista} - {cancion.titulo} ({minutos:02}:{segundos:02})")
            btn_song.setObjectName("btnCancionPlaylistItem")
            btn_song.setStyleSheet("QPushButton { text-align: left; padding: 8px; }")
            btn_song.clicked.connect(lambda checked=False, idx=i, l=playlist_actual_songs: self.reproducir_cancion(idx, l))
            self.layout_pl_songs.addWidget(btn_song)

    def actualizar_vista_artistas(self):
        self.clear_layout(self.layout_artistas_list)
        self.clear_layout(self.layout_artistas_songs)
        
        artistas_unicos = sorted(list(set(song.artista for song in self.playlist)))
        for artista in artistas_unicos:
            btn_art = QPushButton(f"{artista}")
            btn_art.setObjectName("btnArtistaItem")
            btn_art.clicked.connect(lambda checked=False, a=artista: self.cargar_canciones_artista(a))
            self.layout_artistas_list.addWidget(btn_art)

    def cargar_canciones_artista(self, artista):
        self.clear_layout(self.layout_artistas_songs)
        canciones_artista = [song for song in self.playlist if song.artista == artista]
        
        for i, cancion in enumerate(canciones_artista):
            minutos, segundos = cancion.duracion
            btn_song = QPushButton(f"{cancion.titulo} ({minutos:02}:{segundos:02})")
            btn_song.setObjectName("btnCancionArtistaItem")
            btn_song.setStyleSheet("QPushButton { text-align: left; padding: 8px; }")
            btn_song.clicked.connect(lambda checked=False, idx=i, l=canciones_artista: self.reproducir_cancion(idx, l))
            self.layout_artistas_songs.addWidget(btn_song)

    def agregar_al_editor(self, cancion):
        self.editing_playlist_songs.append(cancion)
        self.actualizar_listas_editor()

    def eliminar_del_editor(self, cancion):
        if cancion in self.editing_playlist_songs:
            self.editing_playlist_songs.remove(cancion)
            self.actualizar_listas_editor()

    def cargar_playlist_en_editor(self, index):
        if index <= 0:
            self.txt_playlist_nombre.clear()
            self.editing_playlist_songs = []
            self.actualizar_listas_editor()
            return
        
        nombre_pl = self.cb_playlist_editar.currentText()
        self.txt_playlist_nombre.setText(nombre_pl)
        rutas = cargar_playlist(nombre_pl) 
        
        self.editing_playlist_songs = []
        for r in rutas:
            for song in self.playlist:
                if song.musica == r:
                    self.editing_playlist_songs.append(song)
                    break
        self.actualizar_listas_editor()

    def guardar_playlist_actual(self):
        nombre = self.txt_playlist_nombre.text().strip()
        if not nombre:
            return
        rutas_canciones = [song.musica for song in self.editing_playlist_songs]
        guardar_playlist(nombre, rutas_canciones) 
        self.actualizar_vista_crear()

    def eliminar_playlist_actual(self):
        index = self.cb_playlist_editar.currentIndex()
        if index <= 0:
            return
        nombre_pl = self.cb_playlist_editar.currentText()
        eliminar_playlist(nombre_pl) 
        self.txt_playlist_nombre.clear()
        self.editing_playlist_songs = []
        self.actualizar_vista_crear()

    def filtrar_musica(self, texto):
        texto = texto.lower()
        for widget_boton, cancion in self.lista_widgets_canciones:
            if texto in cancion.titulo.lower() or texto in cancion.artista.lower():
                widget_boton.show()
            else:
                widget_boton.hide()

    def agregar_cancion(self, cancion: data_music):
        self.playlist.append(cancion)
        index_actual = len(self.playlist) - 1
        minutos, segundos = cancion.duracion
        
        texto_boton = f"{cancion.artista} - {cancion.titulo} ({minutos:02}:{segundos:02})"
        boton_reproducir = QPushButton(texto_boton)
        boton_reproducir.setObjectName("btnCancionListaPrincipal")
        boton_reproducir.setStyleSheet("QPushButton { text-align: left; padding: 10px; font-size: 13px; }")
        
        if cancion.imagen and not cancion.imagen.isNull():
            pixmap = QPixmap.fromImage(cancion.imagen).scaled(32, 32)
            boton_reproducir.setIcon(pixmap)

        boton_reproducir.clicked.connect(lambda checked=False, idx=index_actual: self.reproducir_cancion(idx, self.playlist))
        
        self.layout_lista.addWidget(boton_reproducir)
        self.lista_widgets_canciones.append((boton_reproducir, cancion))

    # Nueva función atada al botón del panel derecho con Menú visualmente más grande
    def mostrar_menu_playlists_player(self):
        if self.current_index < 0 or not self.current_playback_list:
            return
            
        cancion_actual = self.current_playback_list[self.current_index]

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                font-size: 14px;
                padding: 5px;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 10px 30px 10px 20px;
            }
        """)
        nombres_playlists = obtener_nombres_playlists() 
        
        if not nombres_playlists:
            accion = menu.addAction("No hay playlists creadas")
            accion.setEnabled(False)
        else:
            for nombre in nombres_playlists:
                accion = menu.addAction(f"Añadir a '{nombre}'")
                accion.triggered.connect(lambda checked=False, n=nombre, c=cancion_actual: self.agregar_cancion_a_playlist_directo(c, n))
        
        menu.exec(self.btn_add_playlist.mapToGlobal(self.btn_add_playlist.rect().bottomRight()))
        
    def agregar_cancion_a_playlist_directo(self, cancion, nombre_pl):
        rutas = cargar_playlist(nombre_pl) 
        if cancion.musica not in rutas:
            rutas.append(cancion.musica)
            guardar_playlist(nombre_pl, rutas) 

    def reproducir_cancion(self, index: int, lista_actual=None): 
        if lista_actual is not None:
            self.current_playback_list = lista_actual
        
        if not self.current_playback_list:
            self.current_playback_list = self.playlist

        if index < 0 or index >= len(self.current_playback_list):
            return
            
        self.current_index = index 
        cancion = self.current_playback_list[index] 
        
        texto_info = (
            f"<b>Reproduciendo:</b> {cancion.titulo}<br>"
            f"<b>Artista:</b> {cancion.artista}<br>"
            f"<b>Ruta:</b> {cancion.musica}"
        )
        self.label_seleccion.setText(texto_info)
        self.lbl_info_derecha.setText(f"<b>{cancion.titulo}</b><br><span style='color: gray;'>{cancion.artista}</span>")

        if cancion.imagen and not cancion.imagen.isNull():
            pixmap = QPixmap.fromImage(cancion.imagen).scaled(
                250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.lbl_caratula.setPixmap(pixmap)
            self.lbl_caratula.setText("")  
        else:
            self.lbl_caratula.setPixmap(QPixmap())
            self.lbl_caratula.setText("Sin carátula")

        self.slider_tiempo.setEnabled(True)
        self.btn_prev.setEnabled(True)
        self.btn_play.setEnabled(True)
        self.btn_next.setEnabled(True)
        self.btn_add_playlist.setEnabled(True) # Ahora se puede hacer clic porque hay una canción cargada

        self.player.setSource(QUrl.fromLocalFile(cancion.musica))
        self.player.play()

    def toggle_reproduccion(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
        
    def cancion_anterior(self):
        if self.current_index > 0:
            self.reproducir_cancion(self.current_index - 1)

    def cancion_siguiente(self):
        if not self.current_playback_list:
            return

        if self.shuffle_activado:
            if len(self.current_playback_list) > 1:
                opciones_validas = list(range(len(self.current_playback_list)))
                opciones_validas.remove(self.current_index)
                nuevo_index = random.choice(opciones_validas)
                self.reproducir_cancion(nuevo_index)
            else:
                self.reproducir_cancion(0)
        else:
            if self.current_index < len(self.current_playback_list) - 1:
                self.reproducir_cancion(self.current_index + 1)
            else:
                self.player.stop() 

    def actualizar_slider(self, posicion):
        self.slider_tiempo.blockSignals(True)
        self.slider_tiempo.setValue(posicion)
        self.slider_tiempo.blockSignals(False)
        
        segundos_totales = posicion // 1000
        minutos = segundos_totales // 60
        segundos = segundos_totales % 60
        self.lbl_tiempo_actual.setText(f"{minutos:02}:{segundos:02}")

    def actualizar_rango_slider(self, posicion):
        self.slider_tiempo.setRange(0, posicion)
        
        segundos_totales = posicion // 1000
        minutos = segundos_totales // 60
        segundos = segundos_totales % 60
        self.lbl_tiempo_total.setText(f"{minutos:02}:{segundos:02}")

    def cambiar_posicion_audio(self, estado):
        self.player.setPosition(estado)
    
    def actualizar_boton_play(self, estado):
        if estado == QMediaPlayer.PlayingState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def cambiar_volumen(self, valor):
        self.audio_output.setVolume(valor / 100.0)


    def actualizar_vista_generos(self):
        self.clear_layout(self.layout_generos_list) 
        self.clear_layout(self.layout_generos_songs)
        self.botones_generos = {}
        self.genero_actual = None
        self.lbl_generos_estado.setText("Selecciona un género para ver sus canciones")
        self.lbl_generos_estado.show()
        
        generos_validos = set()
        for song in self.playlist:
            gen = getattr(song, 'genero', None)
            if gen and str(gen).strip(): 
                generos_validos.add(str(gen).strip())
                
        generos_unicos = sorted(list(generos_validos))

        if not generos_unicos:
            lbl_vacio = QLabel("Aún no hay géneros disponibles")
            lbl_vacio.setObjectName("lblGenerosVacio")
            lbl_vacio.setAlignment(Qt.AlignCenter)
            lbl_vacio.setStyleSheet("padding: 20px;")
            self.layout_generos_list.addWidget(lbl_vacio)
            return
        
        for i, genero in enumerate(generos_unicos):
            cantidad = sum(
                1 for song in self.playlist
                if str(getattr(song, 'genero', '') or '').strip() == genero
            )
            btn_gen = QPushButton(f" {genero} ({cantidad})")
            btn_gen.setObjectName("btnFiltroGenero")
            btn_gen.setIcon(qta.icon('fa5s.tag'))
            btn_gen.setCheckable(True)
            btn_gen.setCursor(Qt.PointingHandCursor)
            
            btn_gen.setProperty("activo", "false")
            btn_gen.setStyleSheet(self.estilo_boton_genero())
            btn_gen.clicked.connect(lambda checked=False, g=genero: self.cargar_canciones_genero(g))
            
            self.botones_generos[genero] = btn_gen
            self.layout_generos_list.addWidget(btn_gen)

    def estilo_boton_genero(self):
        return """
            QPushButton { 
                text-align: left; padding: 6px 10px; 
                font-size: 12px; font-weight: bold; border-radius: 6px;
                border: 1px solid;
            }
        """

    def cargar_canciones_genero(self, genero):
        self.clear_layout(self.layout_generos_songs) 

        if self.genero_actual and self.genero_actual in self.botones_generos:
            btn_prev = self.botones_generos[self.genero_actual]
            btn_prev.setChecked(False)
            btn_prev.setProperty("activo", "false")
            btn_prev.style().unpolish(btn_prev)
            btn_prev.style().polish(btn_prev)
            
        self.genero_actual = genero
        if genero in self.botones_generos:
            btn_actual = self.botones_generos[genero]
            btn_actual.setChecked(True)
            btn_actual.setProperty("activo", "true")
            btn_actual.style().unpolish(btn_actual)
            btn_actual.style().polish(btn_actual)
        
        canciones_genero = []
        for song in self.playlist:
            gen = getattr(song, 'genero', None)
            if gen and str(gen).strip() == genero:
                canciones_genero.append(song)

        if not canciones_genero:
            self.lbl_generos_estado.setText(f"No hay canciones para «{genero}»")
            self.lbl_generos_estado.show()
            return
            
        self.lbl_generos_estado.hide() 
        
        for i, cancion in enumerate(canciones_genero):
            minutos, segundos = cancion.duracion
            btn_song = QPushButton(f"{cancion.artista} - {cancion.titulo} ({minutos:02}:{segundos:02})")
            btn_song.setObjectName("btnSongItemGen")
            btn_song.setCursor(Qt.PointingHandCursor)
            btn_song.setStyleSheet("""
                QPushButton { 
                    text-align: left; padding: 16px 12px; font-size: 12px;
                    border-radius: 8px; border: 1px solid; margin-bottom: 5px;
                }
            """)
            btn_song.clicked.connect(lambda checked=False, idx=i, l=canciones_genero: self.reproducir_cancion(idx, l))
            self.layout_generos_songs.addWidget(btn_song)

    def actualizar_vista_crear(self):
        self.cb_playlist_editar.blockSignals(True) 
        self.cb_playlist_editar.clear()
        self.cb_playlist_editar.addItem("--- Nueva Playlist ---")
        
        nombres = obtener_nombres_playlists() 
        for nombre in nombres:
            self.cb_playlist_editar.addItem(nombre)
        self.cb_playlist_editar.blockSignals(False)

        self.cb_filtrar_genero.blockSignals(True)
        seleccion_previa = self.cb_filtrar_genero.currentText()
        self.cb_filtrar_genero.clear()
        self.cb_filtrar_genero.addItem("Todos los Géneros")
        
        generos_validos = set()
        for song in self.playlist:
            gen = getattr(song, 'genero', None)
            if gen and str(gen).strip():
                generos_validos.add(str(gen).strip())
                
        generos_unicos = sorted(list(generos_validos))
        for gen in generos_unicos:
            self.cb_filtrar_genero.addItem(gen)
                
        index_restaurar = self.cb_filtrar_genero.findText(seleccion_previa)
        if index_restaurar >= 0:
            self.cb_filtrar_genero.setCurrentIndex(index_restaurar)
        self.cb_filtrar_genero.blockSignals(False)
        
        self.actualizar_listas_editor() 

    def actualizar_listas_editor(self):
        self.clear_layout(self.layout_disponibles) 
        self.clear_layout(self.layout_actuales)

        genero_filtrado = self.cb_filtrar_genero.currentText() 

        for cancion in self.playlist:
            if cancion not in self.editing_playlist_songs:
                gen = getattr(cancion, 'genero', None)
                gen_str = str(gen).strip() if gen else ""
                
                if genero_filtrado != "Todos los Géneros" and gen_str != genero_filtrado:
                    continue

                btn_add = QPushButton(f" {cancion.titulo} - {cancion.artista}")
                btn_add.setIcon(qta.icon('fa5s.plus'))
                btn_add.setObjectName("btnPlaylistAdd")
                btn_add.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding: 6px 8px; font-size: 11px;
                        border-radius: 6px; border: 1px solid; margin-bottom: 2px;
                    }
                """)
                btn_add.clicked.connect(lambda checked=False, s=cancion: self.agregar_al_editor(s))
                self.layout_disponibles.addWidget(btn_add)

        for cancion in self.editing_playlist_songs:
            btn_rem = QPushButton(f" {cancion.titulo} - {cancion.artista}")
            btn_rem.setIcon(qta.icon('fa5s.minus'))
            btn_rem.setObjectName("btnPlaylistRem")
            btn_rem.setStyleSheet("""
                QPushButton {
                    text-align: left; padding: 6px 8px; font-size: 11px;
                    border-radius: 6px; border: 1px solid; margin-bottom: 2px;
                }
            """)
            btn_rem.clicked.connect(lambda checked=False, s=cancion: self.eliminar_del_editor(s))
            self.layout_actuales.addWidget(btn_rem)

    def toggle_shuffle(self, activado):
        self.shuffle_activado = activado
        if activado:
            self.btn_shuffle.setProperty("estado", "activo")
        else:
            self.btn_shuffle.setProperty("estado", "inactivo")
            
        self.btn_shuffle.style().unpolish(self.btn_shuffle)
        self.btn_shuffle.style().polish(self.btn_shuffle)

    def verificar_fin_cancion(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.cancion_siguiente()

    def seleccionar_nueva_carpeta(self):
        nueva_carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con música")
        
        if nueva_carpeta:
            guardar_configuracion(nueva_carpeta)
            self.playlist.clear()
            self.lista_widgets_canciones.clear() 
            self.txt_buscar_musica.clear() 
            self.clear_layout(self.layout_lista)
            self.label_seleccion.setText("No hay canción seleccionada")
            
            self.player.stop()
            
            if hasattr(self, 'hilo') and self.hilo.isRunning():
                self.hilo.terminate()
            
            self.hilo = EscaneoMusica(nueva_carpeta)
            self.hilo.cancion.connect(self.agregar_cancion)
            self.hilo.start()

    def eliminar_playlist_desde_lista(self, nombre):
        eliminar_playlist(nombre)
        self.clear_layout(self.layout_pl_songs)
        self.actualizar_vista_playlists()
        self.actualizar_vista_crear()