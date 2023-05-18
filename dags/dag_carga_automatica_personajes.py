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
    url = 'https://rickandmortyapi.com/api/character'
    datos_obtenidos = []

    while url is not None:
        response = requests.get(url)
        data = response.json()
        datos_obtenidos += data['results']
        url = data['info']['next']

    df_personajes = pd.DataFrame(datos_obtenidos)
    df_personajes["origen_name"] = df_personajes["origin"].apply(lambda x: x["name"])
    df_personajes = df_personajes[["id", "name", "status", "species", "type", "gender", "origen_name", "created"]]
    df_personajes.columns = ["id", "nombre", "estado", "especie", "tipo", "genero", "origen", "fecha_creacion"]
    df_personajes.loc[:,"tipo"] =df_personajes["tipo"].replace('','no aplica')
    df_personajes.to_dict('records')


    hook = PostgresHook(postgres_conn_id='amazon_redshift')
    conn = hook.get_conn()
    cur = conn.cursor()
    tabla = "personaje"
    columns = ['id', 'nombre', 'estado', 'especie', 'tipo', 'genero', 'origen', 'fecha_creacion']
    values = [tuple(x) for x in df_personajes.to_numpy()]
    insert_sql = f"INSERT INTO {tabla} ({', '.join(columns)}) VALUES %s"
    cur.execute("BEGIN")
    execute_values(cur, insert_sql, values)
    conn.commit()

    cur.close()
    conn.close()

with DAG(
    default_args=default_args,
    dag_id='carga_de_datos',
    description='Obtener datos de API, transformar y cargar en Redshift',
) as dag:
    task1 = PostgresOperator(
        task_id='crear_tabla',
        postgres_conn_id='amazon_redshift',
        sql="""
            DROP TABLE IF EXISTS jorgeflores2311233_coderhouse.personaje;
            CREATE TABLE jorgeflores2311233_coderhouse.personaje(
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(250),
            estado VARCHAR(250),
            especie VARCHAR(250),
            tipo VARCHAR(250),
            genero VARCHAR(250),
            origen  VARCHAR(250),
            fecha_creacion  TIMESTAMP
            );  
        """
    )

    obtener_datos_task = PythonOperator(
        task_id='obtener_datos',
        python_callable=obtener_datos
    )

    task1 >> obtener_datos_task
