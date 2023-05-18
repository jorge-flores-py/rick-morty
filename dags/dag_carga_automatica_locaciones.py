from datetime import datetime
import requests
import pandas as pd
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from psycopg2.extras import execute_values
import time

default_args = {
    'owner': 'JORGE',
    'start_date': datetime(2023, 5, 18),
    'schedule_interval': '0 0 * * *',
}

def obtener_datos():
    url = 'https://rickandmortyapi.com/api/location'
    datos_obtenidos = []

    while url is not None:
        response = requests.get(url)
        data = response.json()
        datos_obtenidos += data['results']
        url = data['info']['next']

    df_locaciones = pd.DataFrame(datos_obtenidos)
    df_locaciones.to_dict('records')
    df_locaciones = df_locaciones.drop(columns=['residents','url'])
    df_locaciones.columns = ["id", "nombre", "tipo", "dimension", "fecha_creacion"] 
    
    hook = PostgresHook(postgres_conn_id='amazon_redshift')
    conn = hook.get_conn()
    cur = conn.cursor()
    tabla = "locacion"
    columns = ['id', 'nombre', 'tipo', 'dimension', 'fecha_creacion']
    values = [tuple(x) for x in df_locaciones.to_numpy()]
    insert_sql = f"INSERT INTO {tabla} ({', '.join(columns)}) VALUES %s"
    cur.execute("BEGIN")
    execute_values(cur, insert_sql, values)
    conn.commit()
    cur.close()
    conn.close()

with DAG(
    default_args=default_args,
    dag_id='carga_de_locaciones',
    description='Obtener datos de API, transformar y cargar en Redshift',
) as dag:
    crear_tabla = PostgresOperator(
            task_id='crear_tabla_locacion',
            postgres_conn_id='amazon_redshift',
            sql="""
                DROP TABLE IF EXISTS jorgeflores2311233_coderhouse.locacion;
                CREATE TABLE jorgeflores2311233_coderhouse.locacion(
                id INTEGER PRIMARY KEY,
                nombre VARCHAR(250),
                tipo VARCHAR(250),
                dimension VARCHAR(250),
                fecha_creacion DATETIME 
                );  
            """
    )

    obtener_datos_locaciones = PythonOperator(
        task_id='obtener_datos',
        python_callable=obtener_datos
    )

    crear_tabla >> obtener_datos_locaciones
