
import cv2
import numpy as np
import time
from PIL import ImageGrab, ImageTk
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import logging
import sys
from pathlib import Path
from PIL import Image
import re
from typing import Dict, List, Tuple, Optional

from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError, find_windows
from pywinauto.mouse import move, click
from pywinauto.keyboard import send_keys

class DebugImageViewer:
    """Ventana para mostrar imágenes de debugging en tiempo real"""
    
    def __init__(self, parent_logger, parent_log_callback):
        self.logger = parent_logger
        self.log_callback = parent_log_callback
        self.debug_window = None
        self.is_visible = False
        self.image_label = None
        self.info_label = None
        self.current_image = None
        self.current_template = None
        
    def create_debug_window(self):
        """Crea la ventana de debugging"""
        if self.debug_window and self.debug_window.winfo_exists():
            return
            
        self.debug_window = tk.Toplevel()
        self.debug_window.title("Monaco Bot - Debug Visual")
        self.debug_window.geometry("800x700")
        self.debug_window.resizable(True, True)
        
        # Frame principal
        main_frame = ttk.Frame(self.debug_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.debug_window.columnconfigure(0, weight=1)
        self.debug_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Información
        self.info_label = ttk.Label(main_frame, text="Sin imagen", font=("Arial", 10))
        self.info_label.grid(row=0, column=0, pady=(0, 10))
        
        # Frame para imagen con scroll
        image_frame = ttk.Frame(main_frame)
        image_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
        
        # Canvas con scrollbars
        self.canvas = tk.Canvas(image_frame, bg='white')
        v_scrollbar = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(image_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Controles
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=2, column=0, pady=(10, 0))
        
        self.save_button = ttk.Button(controls_frame, text="Guardar Imagen", command=self.save_current_image)
        self.save_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_button = ttk.Button(controls_frame, text="Limpiar", command=self.clear_image)
        self.clear_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Checkbox para mostrar template
        self.show_template_var = tk.BooleanVar(value=True)
        template_check = ttk.Checkbutton(controls_frame, text="Mostrar template", 
                                       variable=self.show_template_var, command=self.update_display)
        template_check.pack(side=tk.LEFT, padx=(5, 0))
        
        # Manejar cierre de ventana
        self.debug_window.protocol("WM_DELETE_WINDOW", self.hide_debug_window)
        
        self.is_visible = True
        
    def show_debug_window(self):
        """Muestra la ventana de debugging"""
        if not self.debug_window or not self.debug_window.winfo_exists():
            self.create_debug_window()
        else:
            self.debug_window.deiconify()
        self.is_visible = True
        
    def hide_debug_window(self):
        """Oculta la ventana de debugging"""
        if self.debug_window and self.debug_window.winfo_exists():
            self.debug_window.withdraw()
        self.is_visible = False
        
    def update_image(self, screenshot_pil, template_path=None, template_image=None, 
                    search_result=None, step_info=""):
        """Actualiza la imagen en la ventana de debugging"""
        if not self.is_visible or not self.debug_window or not self.debug_window.winfo_exists():
            return
            
        try:
            self.current_image = screenshot_pil.copy()
            self.current_template = template_image
            
            # Información del paso actual
            info_text = f"Paso: {step_info}"
            if template_path:
                info_text += f" | Template: {template_path}"
            if search_result:
                info_text += f" | Encontrado en: {search_result}"
            else:
                info_text += " | Template NO encontrado"
                
            self.info_label.config(text=info_text)
            
            self.update_display()
            
        except Exception as e:
            self.logger.error(f"Error actualizando imagen debug: {e}")
    
    def update_display(self):
        """Actualiza la visualización combinando screenshot y template"""
        if not self.current_image:
            return
            
        try:
            display_image = self.current_image.copy()
            
            # Si hay template y está habilitado, combinarlo
            if (self.current_template is not None and 
                self.show_template_var.get()):
                
                # Convertir template de OpenCV a PIL
                template_rgb = cv2.cvtColor(self.current_template, cv2.COLOR_BGR2RGB)
                template_pil = Image.fromarray(template_rgb)
                
                # Crear imagen combinada
                combined_width = display_image.width + template_pil.width + 20
                combined_height = max(display_image.height, template_pil.height) + 40
                
                combined_image = Image.new('RGB', (combined_width, combined_height), 'white')
                
                # Pegar screenshot
                combined_image.paste(display_image, (0, 20))
                
                # Pegar template
                combined_image.paste(template_pil, (display_image.width + 20, 20))
                
                # Añadir etiquetas
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(combined_image)
                try:
                    font = ImageFont.truetype("arial.ttf", 14)
                except:
                    font = ImageFont.load_default()
                
                draw.text((10, 0), "Screenshot", fill='black', font=font)
                draw.text((display_image.width + 30, 0), "Template", fill='black', font=font)
                
                display_image = combined_image
            
            # Redimensionar si es muy grande
            max_display_size = (1200, 800)
            if (display_image.width > max_display_size[0] or 
                display_image.height > max_display_size[1]):
                display_image.thumbnail(max_display_size, Image.Resampling.LANCZOS)
            
            # Convertir a PhotoImage para tkinter
            self.photo = ImageTk.PhotoImage(display_image)
            
            # Actualizar canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            self.logger.error(f"Error actualizando display: {e}")
    
    def save_current_image(self):
        """Guarda la imagen actual"""
        if not self.current_image:
            return
            
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"debug_screenshot_{timestamp}.png"
            self.current_image.save(filename)
            self.log_callback(f"Imagen guardada: {filename}")
        except Exception as e:
            self.logger.error(f"Error guardando imagen: {e}")
    
    def clear_image(self):
        """Limpia la imagen actual"""
        self.canvas.delete("all")
        self.info_label.config(text="Sin imagen")
        self.current_image = None
        self.current_template = None

class PopupDetector:
    """Clase para detectar y manejar ventanas emergentes con reconocimiento de imágenes"""
    
    def __init__(self, logger, log_callback, main_bot):
        self.logger = logger
        self.log_callback = log_callback
        self.main_bot = main_bot  # Referencia al bot principal para usar sus métodos
        self.known_popups = []
        
    def get_all_visible_windows(self) -> List[Dict]:
        """Obtiene todas las ventanas visibles del sistema"""
        windows = []
        try:
            all_handles = find_windows()
            
            for handle in all_handles:
                try:
                    app = Application().connect(handle=handle)
                    window = app.window(handle=handle)
                    
                    # Solo ventanas visibles
                    if window.is_visible() and window.is_enabled():
                        rect = window.rectangle()
                        # Filtrar ventanas muy pequeñas o fuera de pantalla
                        if rect.width() > 50 and rect.height() > 50:
                            window_info = {
                                'handle': handle,
                                'window': window,
                                'title': window.window_text(),
                                'class_name': window.class_name(),
                                'rect': rect,
                                'bbox': (rect.left, rect.top, rect.right, rect.bottom)
                            }
                            windows.append(window_info)
                            
                except Exception:
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error obteniendo ventanas: {e}")
            
        return windows
    
    def is_popup_window(self, window_info: Dict, main_window_handle: int) -> bool:
        """Determina si una ventana es un popup (no es la ventana principal)"""
        try:
            handle = window_info['handle']
            window = window_info['window']
            rect = window_info['rect']
            
            # No es la ventana principal
            if handle == main_window_handle:
                return False
                
            # Características típicas de popups
            title = window_info['title'].lower()
            class_name = window_info['class_name'].lower()
            
            # Indicadores de popup
            popup_indicators = [
                'dialog' in class_name,
                'popup' in class_name,
                window.is_dialog(),
                any(keyword in title for keyword in 
                    ['error', 'warning', 'alert', 'confirm', 'save', 'open', 
                     'advertencia', 'alerta', 'confirmar', 'guardar', 'message']),
                # Ventanas relativamente pequeñas en primer plano
                rect.width() < 800 and rect.height() < 600
            ]
            
            return any(popup_indicators)
            
        except Exception:
            return False
    
    def find_popups_with_images(self, image_patterns: List[str], main_window_handle: int) -> List[Dict]:
        """Busca popups que contengan alguna de las imágenes especificadas"""
        found_popups = []
        
        try:
            all_windows = self.get_all_visible_windows()
            
            for window_info in all_windows:
                if self.is_popup_window(window_info, main_window_handle):
                    # Buscar imágenes en este popup
                    for image_pattern in image_patterns:
                        pos = self.main_bot.find_image_in_window(image_pattern, window_info['bbox'])
                        if pos:
                            popup_data = window_info.copy()
                            popup_data['found_image'] = image_pattern
                            popup_data['image_position'] = pos
                            found_popups.append(popup_data)
                            self.log_callback(f"Popup detectado con imagen '{image_pattern}': {window_info['title']}")
                            break  # Solo necesitamos encontrar una imagen por popup
                            
        except Exception as e:
            self.logger.error(f"Error buscando popups con imágenes: {e}")
            
        return found_popups


class MonacoBot:
    def __init__(self):
        self.setup_logging()
        self.create_gui()
        self.running = False
        self.popup_detector = PopupDetector(self.logger, self.log_to_gui, self)
        self.main_window_handle = None
        self.debug_viewer = DebugImageViewer(self.logger, self.log_to_gui)
        
    def setup_logging(self):
        """Configura el sistema de logging"""
        log_file = Path("monaco_bot.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_gui(self):
        """Crea la interfaz gráfica"""
        self.root = tk.Tk()
        self.root.title("Monaco Bot - Automatización con Detección de Popups")
        self.root.geometry("700x650")
        self.root.resizable(True, True)
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar el grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="Monaco Bot", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Configuración
        config_frame = ttk.LabelFrame(main_frame, text="Configuración", padding="5")
        config_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        ttk.Label(config_frame, text="Ventana objetivo:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.window_var = tk.StringVar(value="Monaco@")
        window_entry = ttk.Entry(config_frame, textvariable=self.window_var)
        window_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Label(config_frame, text="Timeout (seg):").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.timeout_var = tk.StringVar(value="1200")
        timeout_entry = ttk.Entry(config_frame, textvariable=self.timeout_var)
        timeout_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # Configuración de popups
        ttk.Label(config_frame, text="Detección de popups:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.popup_detection_var = tk.BooleanVar(value=True)
        popup_check = ttk.Checkbutton(config_frame, variable=self.popup_detection_var)
        popup_check.grid(row=2, column=1, sticky=tk.W)
        
        # Configuración de imágenes de popup
        popup_images_frame = ttk.LabelFrame(main_frame, text="Imágenes de Popup", padding="5")
        popup_images_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        popup_images_frame.columnconfigure(1, weight=1)
        
        ttk.Label(popup_images_frame, text="Imágenes a buscar en popups:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.popup_images_var = tk.StringVar(value="Ok_button.png,Aceptar_button.png,Close_button.png,Cancel_button.png")
        popup_images_entry = ttk.Entry(popup_images_frame, textvariable=self.popup_images_var)
        popup_images_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Label(popup_images_frame, text="(Separar con comas)", font=("Arial", 8)).grid(row=1, column=1, sticky=tk.W, padx=(0, 5))
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Iniciar Automatización", command=self.start_automation)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Detener", command=self.stop_automation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.test_popup_button = ttk.Button(button_frame, text="Probar Detección Popups", command=self.test_popup_detection)
        self.test_popup_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Barra de progreso
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status
        self.status_var = tk.StringVar(value="Listo para iniciar")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=5, column=0, columnspan=2, sticky=tk.W)
        
        # Log text area
        log_frame = ttk.LabelFrame(main_frame, text="Log de Actividad", padding="5")
        log_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.debug_button = ttk.Button(button_frame, text="Ver Debug Visual", command=self.toggle_debug_window)
        self.debug_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Configurar el grid principal para que se expanda
        main_frame.rowconfigure(6, weight=1)
    
    def get_popup_image_list(self) -> List[str]:
        """Obtiene la lista de imágenes a buscar en popups"""
        images_str = self.popup_images_var.get().strip()
        if not images_str:
            return []
        return [img.strip() for img in images_str.split(',') if img.strip()]
    
    def test_popup_detection(self):
        """Prueba la detección de popups manualmente"""
        self.log_to_gui("=== Probando detección de popups ===")
        
        if not self.main_window_handle:
            # Intentar obtener la ventana principal
            dlg, bbox = self.get_window_and_bbox(self.window_var.get())
            if dlg:
                self.main_window_handle = dlg.handle
        
        popup_images = self.get_popup_image_list()
        self.log_to_gui(f"Buscando popups con imágenes: {popup_images}")
        
        popups = self.popup_detector.find_popups_with_images(popup_images, self.main_window_handle or 0)
        
        if popups:
            self.log_to_gui(f"Se detectaron {len(popups)} ventanas emergentes:")
            for popup in popups:
                self.log_to_gui(f"  - '{popup['title']}' con imagen '{popup['found_image']}'")
        else:
            self.log_to_gui("No se detectaron ventanas emergentes con las imágenes especificadas")
    
    def check_and_handle_popups(self) -> bool:
        """Verifica y maneja ventanas emergentes buscando imágenes específicas"""
        if not self.popup_detection_var.get():
            return False
        
        try:
            popup_images = self.get_popup_image_list()
            if not popup_images:
                return False
                
            popups = self.popup_detector.find_popups_with_images(popup_images, self.main_window_handle or 0)
            
            if popups:
                self.log_to_gui(f"Detectados {len(popups)} popups con imágenes")
                
                for popup in popups:
                    try:
                        # Enfocar el popup
                        popup['window'].set_focus()
                        time.sleep(0.3)
                        
                        # Hacer clic en la imagen encontrada
                        pos = popup['image_position']
                        self.click_at_position(pos)
                        self.log_to_gui(f"Clic en popup '{popup['title']}' en imagen '{popup['found_image']}'")
                        
                        time.sleep(0.5)  # Pausa entre manejo de popups
                        
                    except Exception as e:
                        self.logger.error(f"Error manejando popup: {e}")
                        continue
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error verificando popups: {e}")
        
        return False
        
    def log_to_gui(self, message):
        """Añade mensaje al log de la GUI"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_status(self, status):
        """Actualiza el status en la GUI"""
        self.status_var.set(status)
        self.root.update_idletasks()
        
    def start_automation(self):
        """Inicia la automatización in un hilo separado"""
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.progress.start()
            self.log_text.delete(1.0, tk.END)
            
            # Ejecutar en hilo separado para no bloquear la GUI
            self.automation_thread = threading.Thread(target=self.run_automation, daemon=True)
            self.automation_thread.start()
    
    def stop_automation(self):
        """Detiene la automatización"""
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        self.update_status("Detenido por el usuario")
        self.log_to_gui("Automatización detenida por el usuario")
        
    def load_image_as_cv2(self, image_path):
        """Carga imagen con PIL y la convierte al formato de OpenCV."""
        try:
            with Image.open(image_path) as img:
                img = img.convert('RGB')
                return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.logger.error(f"Error cargando imagen {image_path}: {e}")
            return None

    def resource_path(self, relative_path):
        """Resuelve la ruta relativa respecto al archivo .py"""
        try:
            base_path = getattr(sys, '_MEIPASS', Path(__file__).parent.resolve())
            full_path = Path(base_path) / relative_path
            self.logger.info(f"Ruta de recurso: {full_path}")
            return full_path
        except Exception as e:
            self.logger.error(f"Error resolviendo ruta: {e}")
            return None

    def get_window_and_bbox(self, title_substring):
        """Encuentra y maximiza la ventana objetivo"""
        try:
            self.log_to_gui(f"Buscando ventana con título: {title_substring}")
            app = Application().connect(title_re=f".*{re.escape(title_substring)}.*")
            dlg = app.window(title_re=f".*{re.escape(title_substring)}.*")

            # Guardar el handle de la ventana principal
            self.main_window_handle = dlg.handle

            if not dlg.is_maximized():
                self.log_to_gui("Maximizando ventana...")
                dlg.maximize()
                time.sleep(1)

            dlg.set_focus()
            rect = dlg.rectangle()
            bbox = (rect.left, rect.top, rect.right, rect.bottom)
            self.log_to_gui(f"Ventana encontrada: {title_substring} - {bbox}")
            return dlg, bbox
        except Exception as e:
            self.logger.error(f"Error obteniendo ventana: {e}")
            self.log_to_gui(f"ERROR: No se pudo encontrar la ventana '{title_substring}'")
            return None, None

    def find_image_in_window(self, template_path, window_bbox, threshold=0.9):
        """Busca una imagen template en la ventana especificada"""
        try:
            generalized_template_path = self.resource_path(Path("images") / template_path)
            
            if not generalized_template_path or not generalized_template_path.exists():
                # No loggear como error si estamos buscando en popups
                return None

            screenshot = ImageGrab.grab(bbox=window_bbox)
            
            self.debug_viewer.update_image(
                screenshot_pil=screenshot,
                template_path=str(generalized_template_path),
                template_image=template,
                search_result=center_abs if 'center_abs' in locals() else None,
                step_info=f"Buscando: {template_path}"
            )

            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            template = self.load_image_as_cv2(str(generalized_template_path))
            if template is None:
                return None

            res = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= threshold)
            
            if len(loc[0]) > 0:
                top_left = (loc[1][0], loc[0][0])
                h, w = template.shape[:2]
                center_rel = (top_left[0] + w // 2, top_left[1] + h // 2)
                center_abs = (window_bbox[0] + center_rel[0], window_bbox[1] + center_rel[1])
                return center_abs
            return None
        except Exception as e:
            self.logger.error(f"Error buscando imagen {template_path}: {e}")
            return None

    def click_at_position(self, pos):
        """Hace clic en una posición específica"""
        try:
            move(coords=pos)
            time.sleep(0.2)
            click(coords=pos)
            self.log_to_gui(f"Clic realizado en: {pos}")
        except Exception as e:
            self.logger.error(f"Error haciendo clic en {pos}: {e}")

    def wait_and_click(self, dlg, window_bbox, trigger_img, destination_img, timeout=30):
        """Espera por una imagen trigger y hace clic en la imagen destino"""
        if not self.running:
            return False
            
        self.log_to_gui(f"Esperando imagen: {trigger_img}")
        self.update_status(f"Esperando: {trigger_img}")
        
        start_time = time.time()
        popup_check_interval = 2  # Verificar popups cada 2 segundos
        last_popup_check = 0
        
        while self.running and time.time() - start_time < timeout:
            # Verificar popups periódicamente
            current_time = time.time()
            if current_time - last_popup_check >= popup_check_interval:
                if self.check_and_handle_popups():
                    # Si se manejó un popup, esperar un poco antes de continuar
                    time.sleep(1)
                last_popup_check = current_time
            
            pos_trigger = self.find_image_in_window(trigger_img, window_bbox)
            if pos_trigger:
                self.log_to_gui(f"Imagen detectada: {trigger_img}")
                break
            time.sleep(1)
        
        if not self.running:
            return False
            
        if time.time() - start_time >= timeout:
            self.log_to_gui(f"TIMEOUT esperando: {trigger_img}")
            return False

        # Verificar popups una vez más antes de continuar
        self.check_and_handle_popups()

        self.log_to_gui(f"Buscando destino: {destination_img}")
        pos_dest = self.find_image_in_window(destination_img, window_bbox)
        if pos_dest:
            self.click_at_position(pos_dest)
            # Verificar popups después del clic
            time.sleep(1)
            self.check_and_handle_popups()
            return True
        else:
            self.log_to_gui(f"No se encontró imagen destino: {destination_img}")
            return False

    def wait_for_image_and_type_text(self, dlg, window_bbox, image_path, text_to_type="A-B-C", timeout=30):
        """Espera por una imagen y escribe texto"""
        if not self.running:
            return False
            
        self.log_to_gui(f"Esperando imagen para escribir: {image_path}")
        start_time = time.time()
        popup_check_interval = 2
        last_popup_check = 0
        
        while self.running and time.time() - start_time < timeout:
            # Verificar popups periódicamente
            current_time = time.time()
            if current_time - last_popup_check >= popup_check_interval:
                if self.check_and_handle_popups():
                    time.sleep(1)
                last_popup_check = current_time
            
            pos = self.find_image_in_window(image_path, window_bbox)
            if pos:
                self.log_to_gui(f"Escribiendo texto: '{text_to_type}'")
                self.click_at_position(pos)
                time.sleep(0.5)
                self.click_at_position(pos)
                time.sleep(0.5)
                dlg.set_focus()
                time.sleep(0.3)
                send_keys(text_to_type, with_spaces=True, pause=0.1)
                # Verificar popups después de escribir
                time.sleep(1)
                self.check_and_handle_popups()
                return True
            time.sleep(1)
            
        if not self.running:
            return False
            
        self.log_to_gui("Timeout escribiendo texto")
        return False

    def run_automation(self):
        """Ejecuta la secuencia principal de automatización"""
        try:
            main_window_string = self.window_var.get()
            timeout = int(self.timeout_var.get())
            popup_images = self.get_popup_image_list()
            
            self.log_to_gui("=== Iniciando automatización ===")
            if self.popup_detection_var.get():
                self.log_to_gui(f"Detección de popups ACTIVADA - Imágenes: {popup_images}")
            else:
                self.log_to_gui("Detección de popups DESACTIVADA")
                
            self.update_status("Conectando con la ventana...")

            dlg, bbox = self.get_window_and_bbox(main_window_string)
            if not dlg or not bbox:
                raise Exception(f"No se pudo conectar con la ventana '{main_window_string}'")

            # Verificación inicial de popups
            self.check_and_handle_popups()

            # Secuencia de automatización
            steps = [
                ("Paso 1: Mini Optimize", "Optimize_stage_1.png", "Optimize_stage_1.png"),
                ("Paso 2: End Stage 1", "End_stage_1.png", "Ok_button.png"),
                ("Paso 3: Mini Optimize (2)", "Mini_Optimize_1_button.png", "Mini_Optimize_1_button.png"),
                ("Paso 4: Opt Console", "Opt_console_button.png", "Opt_console_button.png"),
            ]
            
            for step_name, trigger_img, dest_img in steps:
                if not self.running:
                    break
                    
                self.update_status(step_name)
                self.log_to_gui(f"Ejecutando: {step_name}")
                
                success = self.wait_and_click(dlg, bbox, trigger_img, dest_img, timeout)
                if not success:
                    self.log_to_gui(f"ERROR en: {step_name}")
                    break
                    
                time.sleep(1)
            
            if self.running:
                # Pasos adicionales
                self.update_status("Configurando filtro de mensajes")
                self.wait_and_click(dlg, bbox, "message_filter.png", "message_filter.png", timeout)
                self.wait_for_image_and_type_text(dlg, bbox, "message_filter.png", "shapes", timeout)
                
                remaining_steps = [
                    ("End Stage 2", "End_Stage_2.png", "close_opt_console.png"),
                    ("Truncate Stage 2", "Truncate_Stage_2.png", "Truncate_Stage_2.png"),
                    ("Segmentation Complete", "Segmentation_complete.png", "Ok_button.png"),
                    ("Final Dose Calculation", "Final_dose_calculation.png", "disquete.png"),
                ]
                
                for step_name, trigger_img, dest_img in remaining_steps:
                    if not self.running:
                        break
                        
                    self.update_status(step_name)
                    success = self.wait_and_click(dlg, bbox, trigger_img, dest_img, timeout)
                    if not success:
                        self.log_to_gui(f"ERROR en: {step_name}")
                        break
                    time.sleep(1)
            
            if self.running:
                self.log_to_gui("=== Automatización completada exitosamente ===")
                self.update_status("Completado exitosamente")
                messagebox.showinfo("Éxito", "La automatización se completó exitosamente")
            else:
                self.update_status("Automatización detenida")
                
        except Exception as e:
            error_msg = f"ERROR CRÍTICO: {str(e)}"
            self.logger.error(error_msg)
            self.log_to_gui(error_msg)
            self.update_status("Error crítico")
            messagebox.showerror("Error", f"Error en la automatización:\n{str(e)}")
        finally:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress.stop()

    def run(self):
        """Ejecuta la aplicación"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            self.logger.critical(f"Error crítico en la aplicación: {e}")
            
    def on_closing(self):
        """Maneja el cierre de la aplicación"""
        if self.running:
            self.stop_automation()
        self.root.quit()
        self.root.destroy()

    def toggle_debug_window(self):
        """Muestra u oculta la ventana de debugging"""
        if self.debug_viewer.is_visible:
            self.debug_viewer.hide_debug_window()
        else:
            self.debug_viewer.show_debug_window()

def check_dependencies():
    """Verifica que todas las dependencias estén disponibles"""
    missing_deps = []
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        from PIL import Image
    except ImportError:
        missing_deps.append("Pillow")
    
    try:
        import pywinauto
    except ImportError:
        missing_deps.append("pywinauto")
    
    if missing_deps:
        error_msg = f"Faltan dependencias:\n" + "\n".join(f"- {dep}" for dep in missing_deps)
        error_msg += f"\n\nInstala con: pip install {' '.join(missing_deps)}"
        raise ImportError(error_msg)

if __name__ == "__main__":
    try:
        # Verificar dependencias primero
        check_dependencies()
        
        # Crear directorio de logs si no existe
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        app = MonacoBot()
        app.run()
    except ImportError as e:
        # Error de dependencias
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Dependencias Faltantes", str(e))
        sys.exit(1)
    except Exception as e:
        # Otros errores críticos
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error Crítico", f"Error iniciando la aplicación:\n{str(e)}")
        
        # Escribir error a archivo para debugging
        try:
            with open("error_log.txt", "w", encoding="utf-8") as f:
                f.write(f"Error crítico: {str(e)}\n")
                f.write(f"Tipo: {type(e).__name__}\n")
                import traceback
                f.write(f"Traceback:\n{traceback.format_exc()}")
        except:
            pass
            
        sys.exit(1)