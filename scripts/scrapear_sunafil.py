import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# =======================================================
# 📅 ASIGNACIÓN AUTOMÁTICA DE FECHAS (O PARÁMETROS)
# =======================================================
# Para automatizarlo, supongamos que queremos bajar siempre desde el 01/01/2026 hasta hoy
fecha_inicio = "01/01/2026"
fecha_fin = datetime.now().strftime("%d/%m/%Y") 

# =======================================================
# 📂 DEFINIR RUTA DINÁMICA (Local funciona, en Docker también)
# =======================================================
# Buscamos la carpeta 'data/bronze' respecto a donde está el script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
folder_bronze = os.path.join(BASE_DIR, "data", "bronze")

# Asegurar que la carpeta exista, si no, la crea
os.makedirs(folder_bronze, exist_ok=True)

# =======================================================
# ⚙️ CONFIGURAR NAVEGADOR (ADAPTADO PARA DOCKER/HEADLESS)
# =======================================================
options = Options()
options.add_argument("--headless=new") # 👈 Clave para Docker: corre sin abrir ventana
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

options.add_experimental_option("prefs", {
    "download.default_directory": folder_bronze, # 👈 Guarda directo en tu Data Lake Bronze
    "download.prompt_for_download": False,
    "download.directory_upgrade": True
})

# Forzamos a que Selenium use el contenedor remoto que agregamos al Compose
print("🌐 Conectando al contenedor remoto de Chrome...")
driver = webdriver.Remote(
    command_executor='http://selenium-chrome:4444/wd/hub',
    options=options
)

wait = WebDriverWait(driver, 20)

try:
    # =========================
    # 🌐 ABRIR PÁGINA
    # =========================
    url = "https://aplicativosweb5.sunafil.gob.pe/si.consultaResoluciones/consultaResolucion"
    driver.get(url)

    # =========================
    # 🔁 MANEJO DE IFRAME
    # =========================
    time.sleep(3)
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if len(iframes) > 0:
        driver.switch_to.frame(iframes[0])

    # =========================
    # 📝 INGRESAR FECHAS
    # =========================
    inputs = wait.until(EC.presence_of_all_elements_located(
        (By.XPATH, "//input[@type='text']")
    ))

    fecha_inicio_input = inputs[0]
    fecha_fin_input = inputs[1]

    fecha_inicio_input.clear()
    fecha_inicio_input.send_keys(fecha_inicio)

    fecha_fin_input.clear()
    fecha_fin_input.send_keys(fecha_fin)

    # =========================
    # 📥 CLICK EN EXPORTAR EXCEL
    # =========================
    boton_excel = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(., 'Exportar Excel')] | //a[contains(., 'Exportar Excel')]")
    ))
    boton_excel.click()

    # =========================
    # ⏳ ESPERAR DESCARGA
    # =========================
    print(r"📥 Descargando archivo en la zona Bronze...")
    time.sleep(12) # Le damos un par de segundos extra por si acaso

    print(f"✅ Archivo guardado con éxito en: {folder_bronze}")

finally:
    driver.quit()