import os
import time
import glob  # 💡 Necesario para rastrear el archivo descargado por Chrome
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =======================================================
# 📅 RANGO DE FECHAS AUTOMÁTICO (Fase de Ingesta)
# =======================================================
fecha_inicio = "01/01/2026"
fecha_fin = datetime.now().strftime("%d/%m/%Y") 

# =======================================================
# 📂 CONFIGURACIÓN DE RUTA PARA ENTORNO DOCKER (Data Lake)
# =======================================================
folder_bronze = "/opt/airflow/data/1_bronze"
os.makedirs(folder_bronze, exist_ok=True)

# =======================================================
# ⚙️ CONFIGURACIÓN DE CHROME OPTIONS (Headless & Prefs)
# =======================================================
options = Options()
options.add_argument("--headless=new")               
options.add_argument("--no-sandbox")                 
options.add_argument("--disable-dev-shm-usage")     
options.add_argument("--disable-gpu")                 
options.add_argument("--remote-debugging-port=9222") 

options.page_load_strategy = 'eager'

options.add_experimental_option("prefs", {
    "download.default_directory": folder_bronze, 
    "download.prompt_for_download": False,        
    "download.directory_upgrade": True           
})

# =======================================================
# 🌐 CONEXIÓN AL NAVEGADOR REMOTO (Selenium Grid)
# =======================================================
print("🌐 Conectando al contenedor remoto de Chrome...")
driver = webdriver.Remote(
    command_executor='http://selenium_chrome:4444/wd/hub',
    options=options
)

driver.set_page_load_timeout(30)  
driver.implicitly_wait(10)       
wait = WebDriverWait(driver, 20)

try:
    # =======================================================
    # 🌐 NAVEGACIÓN A LA WEB DE SUNAFIL
    # =======================================================
    url = "https://aplicativosweb5.sunafil.gob.pe/si.consultaResoluciones/consultaResolucion"
    driver.get(url)

    # =======================================================
    # 🔁 MANEJO Y CONTROL DE IFRAME
    # =======================================================
    time.sleep(3) 
    
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if len(iframes) > 0:
        driver.switch_to.frame(iframes[0]) 

    # =======================================================
    # 📝 INYECCIÓN DE DATOS EN EL FORMULARIO
    # =======================================================
    inputs = wait.until(EC.presence_of_all_elements_located(
        (By.XPATH, "//input[@type='text']")
    ))

    fecha_inicio_input = inputs[0]
    fecha_fin_input = inputs[1]

    fecha_inicio_input.clear()
    fecha_inicio_input.send_keys(fecha_inicio)

    fecha_fin_input.clear()
    fecha_fin_input.send_keys(fecha_fin)

    # =======================================================
    # 📥 GESTIÓN DEL BOTÓN DE DESCARGA
    # =======================================================
    boton_excel = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(., 'Exportar Excel')] | //a[contains(., 'Exportar Excel')]")
    ))
    boton_excel.click() 

    # =======================================================
    # ⏳ CONTROL DE TIEMPO PARA LA DESCARGA (Buffer)
    # =======================================================
    print("📥 Descargando archivo desde el portal de SUNAFIL...")
    time.sleep(12) # Espera técnica para que los bytes se descarguen por completo

    # =======================================================
    # 🎯 INTERCEPCIÓN Y RENOMBRADO DINÁMICO (Mejora Inmutabilidad)
    # =======================================================
    # Buscamos el archivo base recién descargado por Chrome sin el sufijo numérico
    archivo_original = os.path.join(folder_bronze, "consulta_resoluciones.xls")
    
    if os.path.exists(archivo_original):
        # Generamos el timestamp idéntico al de tus capas Silver y Gold
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nuevo_nombre = os.path.join(folder_bronze, f"consulta_resoluciones_{timestamp}.xls")
        
        # Renombramos el archivo físicamente en el disco
        os.rename(archivo_original, nuevo_nombre)
        print(f"✅ ¡Éxito! Archivo inmutable guardado en Bronze como: {nuevo_nombre}")
    else:
        # En caso de que se haya descargado con un nombre alternativo o se use concurrencia
        print("⚠️ Advertencia: No se encontró el nombre base estándar. Buscando el último .xls...")
        archivos_xls = glob.glob(os.path.join(folder_bronze, "*.xls"))
        # Excluimos archivos que ya tengan una marca de tiempo larga para no renombrarlos dos veces
        archivos_nuevos = [f for f in archivos_xls if "consulta_resoluciones_" not in os.path.basename(f)]
        
        if archivos_nuevos:
            ultimo_descargado = max(archivos_nuevos, key=os.path.getmtime)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nuevo_nombre = os.path.join(folder_bronze, f"consulta_resoluciones_{timestamp}.xls")
            os.rename(ultimo_descargado, nuevo_nombre)
            print(f"✅ Archivo alternativo renombrado con éxito: {nuevo_nombre}")
        else:
            raise FileNotFoundError("❌ Error crítico: El archivo de SUNAFIL no llegó a la carpeta Bronze.")

finally:
    # =======================================================
    # 🧼 LIMPIEZA DE PROCESOS (Garbage Collection)
    # =======================================================
    driver.quit()