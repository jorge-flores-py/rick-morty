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
    url = 'https://rickandmortyapi.com/api/episode'
    datos_obtenidos = []

    while url is not None:
        response = requests.get(url)
        data = response.json()
        datos_obtenidos += data['results']
        url = data['info']['next']

    df_episodios = pd.DataFrame(datos_obtenidos)
    
    df_episodios.to_dict('records')

   
    df_episodios = df_episodios.drop(columns=['characters','url'])
    df_episodios.columns = ["id","nombre_episodio", "fecha_aire", "episodio","fecha_creacion"]

    hook = PostgresHook(postgres_conn_id='amazon_redshift')
    conn = hook.get_conn()
    cur = conn.cursor()
    tabla = "episodio"
    columns = ['id', 'nombre_episodio', 'fecha_aire', 'episodio', 'fecha_creacion']
    values = [tuple(x) for x in df_episodios.to_numpy()]
    insert_sql = f"INSERT INTO {tabla} ({', '.join(columns)}) VALUES %s"
    cur.execute("BEGIN")
    execute_values(cur, insert_sql, values)
    conn.commit()
    cur.close()
    conn.close()

with DAG(
    default_args=default_args,
    dag_id='carga_de_episodios',
    description='Obtener datos de API, transformar y cargar en Redshift',
) as dag:
    crear_tabla = PostgresOperator(
            task_id='crear_tabla_episodio',
            postgres_conn_id='amazon_redshift',
            sql="""
                DROP TABLE IF EXISTS jorgeflores2311233_coderhouse.episodio;
                CREATE TABLE jorgeflores2311233_coderhouse.episodio(
                id INTEGER PRIMARY KEY,
                nombre_episodio VARCHAR(250),
                fecha_aire VARCHAR(250),
                episodio VARCHAR(250),
                fecha_creacion DATETIME
                );  
            """
    )

    obtener_datos_episodios = PythonOperator(
        task_id='obtener_datos',
        python_callable=obtener_datos
    )

    crear_tabla >> obtener_datos_episodios
