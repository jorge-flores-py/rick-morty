from datetime import datetime
import requests
import pandas as pd
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from psycopg2.extras import execute_values

default_args = {
    'owner': 'JORGE',
    'start_date': datetime(2023, 5, 17),
    'schedule_interval': '0 0 * * *',
}

def obtener_datos_personajes():
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

    return df_personajes.to_dict('records')

def obtener_datos_capitulos():
    url = 'https://rickandmortyapi.com/api/episode'
    datos_obtenidos = []

    while url is not None:
        response = requests.get(url)
        data = response.json()
        datos_obtenidos += data['results']
        url = data['info']['next']

    df_capitulos = pd.DataFrame(datos_obtenidos)
    df_capitulos["air_date"] = pd.to_datetime(df_capitulos["air_date"])
    df_capitulos = df_capitulos[["id", "name", "air_date", "episode"]]
    df_capitulos.columns = ["id", "nombre", "fecha_emision", "codigo"]

    return df_capitulos.to_dict('records')

def cargar_datos(df_datos, tabla):
    hook = PostgresHook(postgres_conn_id='amazon_redshift')
    conn = hook.get_conn()
    cur = conn.cursor()

    columns = list(df_datos.columns)
    values = [tuple(x) for x in df_datos.to_numpy()]
    insert_sql = f"INSERT INTO {tabla} ({', '.join(columns)}) VALUES %s"
    cur.execute("BEGIN")
    execute_values(cur, insert_sql, values)
    conn.commit()

    cur.close()
    conn.close()

with DAG(
    default_args=default_args,
    dag_id='carga_de_datos2',
    description='Obtener datos de API, transformar y cargar en Redshift',
) as dag:
    task_crear_tabla_personajes = PostgresOperator(
        task_id='crear_tabla_personajes',
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
            origen VARCHAR(250),
            fecha_creacion TIMESTAMP
            );  
        """
    )

    task_obtener_datos_personajes = PythonOperator(
        task_id='obtener_datos_personajes',
        python_callable=obtener_datos_personajes
    )

    task_cargar_personajes = PythonOperator(
        task_id='cargar_personajes',
        python_callable=cargar_datos,
        op_kwargs={'df_datos': task_obtener_datos_personajes.output, 'tabla': 'jorgeflores2311233_coderhouse.personaje'}
    )

    task_crear_tabla_capitulos = PostgresOperator(
        task_id='crear_tabla_capitulos',
        postgres_conn_id='amazon_redshift',
        sql="""
            DROP TABLE IF EXISTS jorgeflores2311233_coderhouse.capitulo;
            CREATE TABLE jorgeflores2311233_coderhouse.capitulo(
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(250),
            fecha_emision TIMESTAMP,
            codigo VARCHAR(250)
            );  
        """
    )

    task_obtener_datos_capitulos = PythonOperator(
        task_id='obtener_datos_capitulos',
        python_callable=obtener_datos_capitulos
    )

    task_cargar_capitulos = PythonOperator(
        task_id='cargar_capitulos',
        python_callable=cargar_datos,
        op_kwargs={'df_datos': task_obtener_datos_capitulos.output, 'tabla': 'jorgeflores2311233_coderhouse.capitulo'}
    )

    task_crear_tabla_personajes >> task_obtener_datos_personajes >> task_cargar_personajes
    task_crear_tabla_capitulos >> task_obtener_datos_capitulos >> task_cargar_capitulos
