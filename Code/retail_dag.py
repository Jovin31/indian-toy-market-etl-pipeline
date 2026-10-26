from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Konfigurasi Dasar Airflow
default_args = {
    'owner': 'udeen',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'indian_toy_market_pipeline', # Nama DAG
    default_args=default_args,
    description='End-to-End ETL Pipeline for Indian Toy Market Data',
    schedule='@daily',
    start_date=datetime(2026, 5, 21),
    catchup=False,
) as dag:
    task_ingestion = BashOperator(
        task_id='data_ingestion_stage',
        bash_command='python3 /opt/airflow/dags/ingest_data.py'
    )
    task_transformation = BashOperator(
        task_id='data_transformation_stage',
        bash_command='python3 /opt/airflow/dags/transform_data_v2.py'
    )

    task_ingestion >> task_transformation