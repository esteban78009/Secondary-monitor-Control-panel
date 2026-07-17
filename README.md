# Secondary monitor Control panel

Un panel de control personalizable y modular, diseñado con el fin de aprovechar monitores secundarios tactiles cuenta con reproductor de musica , monitoreo de hardware , posibilidad de poner wallpaper con wallpaper engine u imagenes y metodo de expansion mediante addons

## *Características principales*

- *Gestión de Música:* Reproductor local con soporte para listas de reproducción, navegación por artistas/géneros y control de volumen.
(https://github.com/esteban78009/Secondary-monitor-Control-panel/blob/313675206a712351da82f4013d147b51a2ff925e/screenshots/musica.png)

- *Monitoreo de Sistema:* Visualización en tiempo real del uso de CPU, RAM, almacenamiento y temperaturas (integración con OpenHardwareMonitor).

(https://github.com/esteban78009/Secondary-monitor-Control-panel/blob/313675206a712351da82f4013d147b51a2ff925e/screenshots/monitorizacion.png)

- *Gestor de Wallpapers:* Configuración avanzada de fondos de pantalla con integración completa para múltiples monitores.

(https://github.com/esteban78009/Secondary-monitor-Control-panel/blob/313675206a712351da82f4013d147b51a2ff925e/screenshots/wallpaper.png)

- *Sistema de Addons:* Arquitectura extensible que permite crear y cargar nuevas secciones de forma dinámica sin modificar el núcleo del programa , viene integrado con un addon de pomodoro.

(https://github.com/esteban78009/Secondary-monitor-Control-panel/blob/313675206a712351da82f4013d147b51a2ff925e/screenshots/pomodoro.png)

- *Interfaz Táctil Amigable:* Diseñado con PySide6 para ser responsivo y fácil de usar en pantallas pequeñas o táctiles.

## Librerias usadas

- *pyside*
- *QTAwesome*
- *Psutil / wmi*
- *tinyTag*

Ademas es necesario tener descargado OpenHardwareMonitor y tenerlo en segundo plano para que todo el monitoreo funcione de forma correcta

## Instalacion

Clona el repositorio:

```bash
git clone https://github.com/esteban78009/Secondary-monitor-Control-panel.git
cd Secondary-monitor-Control-panel
```

```bash
pip install -r requirements.txt
```


```bash
python main.py
```

## Integración con Wallpapers

Este proyecto es compatible con mi [proyecto de wallpapers para yasb](https://github.com/esteban78009/yasb-multiple-monitor-wallpaper-Wallpaper-engine-integration) de tal forma que en caso de tener este, permite el uso de ambos modos de gestionar wallpapers de forma simultanea.

