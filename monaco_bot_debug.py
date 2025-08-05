import cv2
import numpy as np
import time
from PIL import ImageGrab
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import logging
import sys
from pathlib import Path
from PIL import Image
import re

from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.mouse import move, click
from pywinauto.keyboard import send_keys


class MonacoBot:
    def __init__(self):
        self.setup_logging()
        self.create_gui()
        self.running = False
        
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
        self.root.title("Monaco Bot - Automatización")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar el grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
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
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Iniciar Automatización", command=self.start_automation)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Detener", command=self.stop_automation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Barra de progreso
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status
        self.status_var = tk.StringVar(value="Listo para iniciar")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=4, column=0, columnspan=2, sticky=tk.W)
        
        # Log text area
        log_frame = ttk.LabelFrame(main_frame, text="Log de Actividad", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar el grid principal para que se expanda
        main_frame.rowconfigure(5, weight=1)
        
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
        """Busca una imagen template en la ventana"""
        try:
            generalized_template_path = self.resource_path(Path("images") / template_path)
            
            if not generalized_template_path or not generalized_template_path.exists():
                self.log_to_gui(f"ERROR: No se encontró la imagen: {template_path}")
                return None

            screenshot = ImageGrab.grab(bbox=window_bbox)
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
        while self.running and time.time() - start_time < timeout:
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

        self.log_to_gui(f"Buscando destino: {destination_img}")
        pos_dest = self.find_image_in_window(destination_img, window_bbox)
        if pos_dest:
            self.click_at_position(pos_dest)
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
        
        while self.running and time.time() - start_time < timeout:
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
            
            self.log_to_gui("=== Iniciando automatización ===")
            self.update_status("Conectando con la ventana...")

            dlg, bbox = self.get_window_and_bbox(main_window_string)
            if not dlg or not bbox:
                raise Exception(f"No se pudo conectar con la ventana '{main_window_string}'")

            # Secuencia de automatización
            steps = [
                ("Paso 1: Mini Optimize", "Mini_Optimize_1_button.png", "Mini_Optimize_1_button.png"),
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