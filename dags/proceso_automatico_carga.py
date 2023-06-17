import requests
import pandas as pd
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'retries': 1
}

def obtener_y_transformar_datos():
    url = "https://rickandmortyapi.com/api/character"
    datos_obtenidos = []

    while url is not None:
        response = requests.get(url)
        data = response.json()
        datos_obtenidos += data['results']
        url = data['info']['next']

    df = pd.DataFrame(datos_obtenidos)
    df["origen_name"] = df["origin"].apply(lambda x: x["name"])
    df = df[["id", "name", "status", "species", "type", "gender", "origen_name", "created"]]
    df.columns = ["id", "nombre", "estado", "especie", "tipo", "genero", "origen", "fecha_creacion"]
    df.loc[:, "tipo"] = df["tipo"].replace('', 'no aplica')

    # Aquí puedes realizar cualquier otra operación o guardar el DataFrame en algún lugar

dag = DAG(
    'rick_and_morty_dag',
    default_args=default_args,
    schedule_interval=None
)

obtener_y_transformar_datos_task = PythonOperator(
    task_id='obtener_y_transformar_datos',
    python_callable=obtener_y_transformar_datos,
    dag=dag
)

obtener_y_transformar_datos_task
