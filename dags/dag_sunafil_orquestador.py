from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'tu_nombre',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id="orquestador_sunafil_bronze",
    default_args=default_args,
    description="DAG que ejecuta el script de Selenium para SUNAFIL",
    schedule_interval=None,          # Manual por ahora
    start_date=datetime(2026, 1, 1), 
    catchup=False,
    tags=['sunafil', 'bronze'],
) as dag:

    ejecutar_scraping = BashOperator(
        task_id="ejecutar_selenium_sunafil",
        # Dentro de Docker, la carpeta 'scripts' se lee en esta ruta interna:
        bash_command="python /opt/airflow/scripts/scrapear_sunafil.py"
    )

    ejecutar_scraping