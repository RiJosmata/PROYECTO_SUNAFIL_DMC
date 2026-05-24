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
# 📅 RANGO DE FECHAS AUTOMÁTICO (Fase de Ingesta)
# =======================================================
# Automatiza el rango: desde el inicio de año hasta el día exacto de la ejecución.
fecha_inicio = "01/01/2026"
fecha_fin = datetime.now().strftime("%d/%m/%Y") # Convierte la fecha de hoy a formato DD/MM/YYYY

# =======================================================
# 📂 CONFIGURACIÓN DE RUTA PARA ENTORNO DOCKER (Data Lake)
# =======================================================
# Forzamos la ruta interna del contenedor compartida con Windows mediante el volumen de Docker.
# Esto garantiza que el Chrome remoto escriba en la carpeta mapeada del host.
folder_bronze = "/opt/airflow/data/bronze"

# Medida de seguridad: Si la carpeta 'data/bronze' no existe localmente, Python la crea en un milisegundo.
os.makedirs(folder_bronze, exist_ok=True)

# =======================================================
# ⚙️ CONFIGURACIÓN DE CHROME OPTIONS (Headless & Prefs)
# =======================================================
options = Options()
options.add_argument("--headless=new") # 👈 Obligatorio para Docker: corre en segundo plano sin interfaz gráfica
options.add_argument("--no-sandbox")   # Desactiva el modo sandbox (necesario para entornos basados en contenedores Linux)
options.add_argument("--disable-dev-shm-usage") # Evita caídas del navegador limitando el uso de memoria compartida (/dev/shm)

# Configuramos el comportamiento de las descargas en el navegador remoto
options.add_experimental_option("prefs", {
    "download.default_directory": folder_bronze, # 👈 Indica al Chrome remoto la ruta exacta donde depositar el Excel
    "download.prompt_for_download": False,        # Desactiva la ventana emergente de confirmación de descarga
    "download.directory_upgrade": True           # Sobrescribe configuraciones previas de directorios de descarga
})

# =======================================================
# 🌐 CONEXIÓN AL NAVEGADOR REMOTO (Selenium Grid)
# =======================================================
print("🌐 Conectando al contenedor remoto de Chrome...")
# Conecta el script de Airflow con el contenedor independiente 'selenium-chrome' usando el puerto 4444
driver = webdriver.Remote(
    command_executor='http://selenium-chrome:4444/wd/hub',
    options=options
)

# Explicit Wait: Espera inteligente de hasta 20 segundos para que aparezcan los elementos web antes de lanzar error
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
    time.sleep(3) # Espera técnica de 3 segundos para que cargue la estructura base de la página
    
    # La SUNAFIL incrusta su formulario dentro de una "sub-página" llamada iframe.
    # Selenium no puede tocar los botones si no se cambia de contexto primero.
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if len(iframes) > 0:
        driver.switch_to.frame(iframes[0]) # Se mete al primer iframe encontrado para desbloquear los inputs

    # =======================================================
    # 📝 INYECCIÓN DE DATOS EN EL FORMULARIO
    # =======================================================
    # Espera a que los inputs de tipo texto estén presentes en el DOM del iframe
    inputs = wait.until(EC.presence_of_all_elements_located(
        (By.XPATH, "//input[@type='text']")
    ))

    # Identifica las cajas por posición: el primer input es Desde (Inicio) y el segundo es Hasta (Fin)
    fecha_inicio_input = inputs[0]
    fecha_fin_input = inputs[1]

    # Limpia cualquier valor por defecto y digita las variables calculadas al inicio
    fecha_inicio_input.clear()
    fecha_inicio_input.send_keys(fecha_inicio)

    fecha_fin_input.clear()
    fecha_fin_input.send_keys(fecha_fin)

    # =======================================================
    # 📥 GESTIÓN DEL BOTÓN DE DESCARGA
    # =======================================================
    # XPath robusto: Busca cualquier botón o enlace que contenga el texto exacto 'Exportar Excel'
    boton_excel = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(., 'Exportar Excel')] | //a[contains(., 'Exportar Excel')]")
    ))
    boton_excel.click() # Lanza el evento de descarga

    # =======================================================
    # ⏳ CONTROL DE TIEMPO PARA LA DESCARGA (Buffer)
    # =======================================================
    print(r"📥 Descargando archivo en la zona Bronze...")
    # Congela el script por 12 segundos. Esto es vital ya que las descargas en modo Headless se cancelan
    # inmediatamente si el proceso del driver se cierra antes de terminar de recibir los bytes del servidor.
    time.sleep(12) 

    print(f"✅ Archivo guardado con éxito en la zona compartida: {folder_bronze}")

finally:
    # =======================================================
    # 🧼 LIMPIEZA DE PROCESOS (Garbage Collection)
    # =======================================================
    # Crucial en entornos de producción: Cierra todas las ventanas, sesiones y mata los subprocesos 
    # de Chrome abiertos en el contenedor remoto para liberar memoria RAM.
    driver.quit()