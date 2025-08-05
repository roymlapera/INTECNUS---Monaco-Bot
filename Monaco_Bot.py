import cv2
import numpy as np
import time
from PIL import ImageGrab

from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.mouse import move, click
from pywinauto.keyboard import send_keys

import re
import sys
from pathlib import Path

from PIL import Image

def load_image_as_cv2(image_path):
    """Carga imagen con PIL y la convierte al formato de OpenCV."""
    with Image.open(image_path) as img:
        img = img.convert('RGB')  # asegura 3 canales
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def resource_path(relative_path):
    """Resuelve la ruta relativa respecto al archivo .py"""
    base_path = getattr(sys, '_MEIPASS', Path(__file__).parent.resolve())
    return Path(base_path) / relative_path


def get_window_and_bbox(title_substring):
    app = Application().connect(title_re=f".*{re.escape(title_substring)}.*")
    dlg = app.window(title_re=f".*{re.escape(title_substring)}.*")

    if not dlg.is_maximized():
        print("Maximizando ventana...")
        dlg.maximize()
        time.sleep(1)  # Pequeño delay para que se renderice correctamente

    dlg.set_focus()
    rect = dlg.rectangle()
    print(f"Ventana encontrada y maximizada: {title_substring} con bbox {rect}")
    return dlg, (rect.left, rect.top, rect.right, rect.bottom)

def find_image_in_window(template_path, window_bbox, threshold=0.9):
    generalized_template_path = resource_path(Path("images") / template_path)
    print(f"Buscando imagen en: {generalized_template_path}")

    if not generalized_template_path.exists():
        raise FileNotFoundError(f"No se encontró la imagen: {generalized_template_path}")

    screenshot = ImageGrab.grab(bbox=window_bbox)
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    template = load_image_as_cv2(str(generalized_template_path))
    if template is None:
        raise ValueError(f"No se pudo cargar la imagen: {generalized_template_path}")

    res = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    
    if len(loc[0]) > 0:
        top_left = (loc[1][0], loc[0][0])
        h, w = template.shape[:2]
        center_rel = (top_left[0] + w // 2, top_left[1] + h // 2)
        center_abs = (window_bbox[0] + center_rel[0], window_bbox[1] + center_rel[1])
        return center_abs
    return None

def click_at_position(pos):
    move(coords=pos)
    click(coords=pos)

def wait_and_click(dlg, window_bbox, trigger_img, destination_img, timeout=30):
    print("Esperando trigger...")
    start_time = time.time()
    while True:
        pos_trigger = find_image_in_window(trigger_img, window_bbox)
        if pos_trigger:
            print(f"Trigger detectado en {pos_trigger}")
            break
        elif time.time() - start_time > timeout:
            print("Timeout esperando trigger!")
            return False
        time.sleep(1)

    print("Buscando destino...")
    pos_dest = find_image_in_window(destination_img, window_bbox)
    if pos_dest:
        print(f"Destino encontrado en {pos_dest}, haciendo clic")
        click_at_position(pos_dest)
        return True
    else:
        print("No se encontró imagen destino")
        return False

def wait_for_image_and_type_text(dlg, window_bbox, image_path, text_to_type="A-B-C", timeout=30):
    print("Esperando a que aparezca la imagen...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        pos = find_image_in_window(image_path, window_bbox)
        if pos:
            print(f"Imagen detectada en {pos}, escribiendo '{text_to_type}'")
            click_at_position(pos)
            time.sleep(0.5)
            click_at_position(pos)  # Segundo clic para asegurar el foco
            time.sleep(0.5)
            dlg.set_focus()
            time.sleep(0.3)
            send_keys(text_to_type, with_spaces=True, pause=0.1)
            return True
        time.sleep(1)
    print("Timeout sin detectar imagen.")
    return False

# --- Secuencia principal automatizada ---

if __name__ == "__main__":
    main_window_string = "Monaco@"
    optconsole_window_string = "Optimization"
    timeout = 1200

    try:
        dlg, bbox = get_window_and_bbox(main_window_string)
        wait_and_click(dlg, bbox, "Mini_Optimize_1_button.png", "Mini_Optimize_1_button.png", timeout)
        wait_and_click(dlg, bbox, "End_stage_1.png", "Ok_button.png", timeout)
        wait_and_click(dlg, bbox, "Mini_Optimize_1_button.png", "Mini_Optimize_1_button.png", timeout)
        wait_and_click(dlg, bbox, "Opt_console_button.png", "Opt_console_button.png", timeout)

        time.sleep(1)  # Espera 1 segundo antes de buscar la nueva ventana

        wait_and_click(dlg, bbox, "message_filter.png", "message_filter.png", timeout)
        wait_for_image_and_type_text(dlg, bbox, "message_filter.png", "shapes", timeout)
        wait_and_click(dlg, bbox, "End_Stage_2.png", "close_opt_console.png", timeout)

        time.sleep(1)  # Espera 1 segundo antes de buscar la nueva ventana

        wait_and_click(dlg, bbox, "Truncate_Stage_2.png", "Truncate_Stage_2.png", timeout)
        wait_and_click(dlg, bbox, "Segmentation_complete.png", "Ok_button.png", timeout)
        wait_and_click(dlg, bbox, "Final_dose_calculation.png", "disquete.png", timeout)
    except ElementNotFoundError:
        print(f"No se encontró la ventana con '{main_window_string}' en el título.")



