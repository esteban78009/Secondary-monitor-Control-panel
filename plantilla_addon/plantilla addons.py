"""
PLANTILLA PARA ADDONS - PANEL DE CONTROL
========================================
Instrucciones:
1. Copia este archivo y cámbiale el nombre (ej: block_notas.py).
2. Cambia el nombre de la clase 'MiAddonApp' por algo descriptivo.
3. Modifica la función 'cargar_addon()' al final del archivo para devolver
   el nombre real de tu addon y la instancia de tu clase.
4. ¡Empieza a programar dentro de _construir_interfaz()!
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)

class MiAddonApp(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. Configura aquí tus variables de estado o temporizadores
        self.mi_variable = "¡Hola Mundo!"
        
        # 2. Llamada a la construcción de la interfaz
        self._construir_interfaz()

    def _construir_interfaz(self):
        # Layout principal de tu Addon
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(20)
        
        # --- EJEMPLO DE INTERFAZ ---
        # Contenedor con estilo para que haga juego con el resto del programa
        marco = QFrame()
        marco.setStyleSheet("""
            QFrame { background-color: #181825; border-radius: 15px; border: 2px solid #313244; }
            QLabel { color: #cdd6f4; border: none; }
        """)
        layout_marco = QVBoxLayout(marco)
        
        # Etiqueta de Título
        titulo = QLabel("Bienvenido a tu nuevo Addon")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #cba6f7;")
        
        # Botón de ejemplo
        self.btn_accion = QPushButton("Haz click aquí")
        self.btn_accion.setCursor(Qt.PointingHandCursor)
        self.btn_accion.setStyleSheet("""
            QPushButton { background-color: #313244; color: #cdd6f4; font-size: 16px; font-weight: bold; padding: 10px; border-radius: 8px; border: 1px solid #45475a; }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #cba6f7; color: #11111b; }
        """)
        self.btn_accion.clicked.connect(self._ejecutar_accion)
        
        layout_marco.addWidget(titulo)
        layout_marco.addSpacing(20)
        layout_marco.addWidget(self.btn_accion)
        
        # Agregamos el marco al layout principal y empujamos todo hacia arriba
        layout_principal.addWidget(marco)
        layout_principal.addStretch()

    # --- TUS FUNCIONES LÓGICAS AQUÍ ---
    def _ejecutar_accion(self):
        print(f"El botón fue presionado. Estado: {self.mi_variable}")
        self.btn_accion.setText("¡Acción completada!")
        self.btn_accion.setStyleSheet(self.btn_accion.styleSheet().replace("#313244", "#a6e3a1").replace("#cdd6f4", "#11111b"))

# ==========================================
# EL CONTRATO DEL ADDON (OBLIGATORIO)
# ==========================================
def cargar_addon():
    """
    El motor de addons en main.py buscará esta función.
    Debes devolver una Tupla con: (Nombre_del_Boton, Instancia_del_Widget)
    """
    # 1. Instancia tu clase principal
    widget = MiAddonApp()
    
    # 2. Retorna el nombre que saldrá en la barra superior y la instancia
    return "Plantilla Addon", widget