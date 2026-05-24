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
    dag_id="orquestador_sunafil_bronze",  # El identificador único que ves en la interfaz web de Airflow
    default_args=default_args,            # Carga las configuraciones por defecto definidas arriba
    description="DAG que ejecuta el script de Selenium para SUNAFIL", # Pequeña ayuda visual para el equipo
    schedule_interval=None,               # Configurado en 'None' para que solo se ejecute manualmente (Trigger)
    start_date=datetime(2026, 1, 1),      # Fecha de nacimiento del DAG en el sistema
    catchup=False,                        # Evita que Airflow intente ejecutar los días pasados desde el start_date
    tags=['sunafil', 'bronze'],           # Etiquetas para buscar y filtrar este DAG rápidamente en la web
) as dag:

    # =======================================================
    # 🏃‍♂️ TAREA 1: EJECUTAR EL SCRAPING EN CONSOLA
    # =======================================================
    # Usamos un BashOperator porque queremos lanzar un comando directo en la terminal de Linux de Airflow.
    ejecutar_scraping = BashOperator(
        task_id="ejecutar_selenium_sunafil", # Nombre del cuadradito que cambia de color en Airflow
        
        # Comando de consola: Ejecuta Python apuntando a la ruta compartida interna de Docker.
        # Recuerda que '/opt/airflow/' es la raíz dentro del contenedor.
        bash_command="python /opt/airflow/scripts/scrapear_sunafil.py"
    )

    # =======================================================
    # 🔀 FLUJO DE DEPENDENCIAS
    # =======================================================
    # Aquí se define el orden en que se ejecutan las tareas. 
    # Al declarar 'ejecutar_scraping', Airflow sabe que debe iniciar este proceso.
    ejecutar_scraping