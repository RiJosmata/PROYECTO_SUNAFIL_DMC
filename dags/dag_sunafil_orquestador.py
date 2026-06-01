from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# =======================================================
# ⚙️ CONFIGURACIÓN POR DEFECTO PARA LAS TAREAS (Arguments)
# =======================================================
# Estas reglas se aplicarán automáticamente a cualquier tarea dentro de este DAG.
default_args = {
    'owner': 'Grupo_5',           # Nombre del ingeniero responsable del flujo
    'depends_on_past': False,       # Si una ejecución falla, las del día siguiente pueden correr igual
    'email_on_failure': False,      # Desactiva alertas automáticas por correo si algo falla
    'email_on_retry': False,        # Desactiva alertas por correo durante los reintentos
    'retries': 1,                   # Si la tarea falla (ej. caída de la web de SUNAFIL), reintenta 1 vez
    'retry_delay': timedelta(minutes=5), # Espera 5 minutos antes de lanzar el reintento automático
}

# =======================================================
# 🧠 DEFINICIÓN DEL ORQUESTADOR (DAG)
# =======================================================
with DAG(
    dag_id="orquestador_sunafil_medallion",  # 💡 CORREGIDO: Refleja que controla todo el flujo Medallón
    default_args=default_args,            # Carga las configuraciones por defecto definidas arriba
    description="DAG completo que ejecuta Scraping (Bronze), Limpieza (Silver) y Modelado (Gold) para SUNAFIL", # 💡 Actualizado
    schedule_interval=None,               # Configurado en 'None' para que solo se ejecute manualmente (Trigger)
    start_date=datetime(2026, 1, 1),      # Fecha de nacimiento del DAG en el sistema
    catchup=False,                        # Evita que Airflow intente ejecutar los días pasados desde el start_date
    tags=['sunafil', 'medallion', 'pipeline'], # 💡 Actualizado para búsquedas rápidas
) as dag:

    # =======================================================
    # 🏃‍♂️ TAREA 1: CAPA BRONZE - WEB SCRAPING EN CONSOLA
    # =======================================================
    # Lanza tu script de Selenium actualizado.
    tarea_bronze = BashOperator(
        task_id="ejecutar_selenium_sunafil_bronze", 
        bash_command="python /opt/airflow/scripts/scrapear_sunafil_bronze.py"
    )

    # =======================================================
    # 🏃‍♂️ TAREA 2: CAPA SILVER - LIMPIEZA Y ESTANDARIZACIÓN
    # =======================================================
    # Lanza el script encargado de limpiar de forma independiente las Resoluciones y el Ubigeo.
    tarea_silver = BashOperator(
        task_id='limpiar_datos_silver',
        bash_command='python /opt/airflow/scripts/limpiar_silver.py'
    )

    # =======================================================
    # 🏃‍♂️ TAREA 3: CAPA GOLD - CRUCES Y LÓGICA DE NEGOCIO
    # =======================================================
    # Lanza el script que realiza el Join y genera la columna calculada para Power BI.
    tarea_gold = BashOperator(
        task_id='modelar_datos_gold',
        bash_command='python /opt/airflow/scripts/modelar_gold.py'
    )

    # =======================================================
    # 🔀 FLUJO DE DEPENDENCIAS (PIPELINE)
    # =======================================================
    # Establece el flujo ordenado de datos de izquierda a derecha.
    tarea_bronze >> tarea_silver >> tarea_gold