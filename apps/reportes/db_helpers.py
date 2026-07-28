import os
import psycopg2


def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


def conectar_visualizador():
    return psycopg2.connect(
        host=get_required_env("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=get_required_env("POSTGRES_DB"),
        user=get_required_env("POSTGRES_USER"),
        password=get_required_env("POSTGRES_PASSWORD"),
    )


def conectar_ra():
    return psycopg2.connect(
        host=get_required_env("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=get_required_env("DB_NAME2"),
        user=get_required_env("POSTGRES_USER"),
        password=get_required_env("POSTGRES_PASSWORD"),
    )


def obtener_dblink_visualizador():
    return (
        f"dbname={get_required_env('POSTGRES_DB')} "
        f"user={get_required_env('POSTGRES_USER')} "
        f"password={get_required_env('POSTGRES_PASSWORD')} "
        f"host={get_required_env('POSTGRES_HOST')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')}"
    )


def obtener_dblink_padron():
    return (
        f"dbname={get_required_env('PADRON_DB_NAME')} "
        f"user={get_required_env('PADRON_DB_USER')} "
        f"password={get_required_env('PADRON_DB_PASSWORD')} "
        f"host={get_required_env('PADRON_DB_HOST')} "
        f"port={os.getenv('PADRON_DB_PORT', '5432')}"
    )


def conectar_evaluacion():
    return psycopg2.connect(
        host=get_required_env("POSTGRES_HOST_EVALUACION"),
        port=os.getenv("POSTGRES_PORT_EVALUACION", "5432"),
        database=get_required_env("POSTGRES_DB_EVALUACION"),
        user=get_required_env("POSTGRES_USER_EVALUACION"),
        password=get_required_env("POSTGRES_PASSWORD_EVALUACION"),
    )


def obtener_dblink_evaluacion():
    return (
        f"dbname={get_required_env('POSTGRES_DB_EVALUACION')} "
        f"user={get_required_env('POSTGRES_USER_EVALUACION')} "
        f"password={get_required_env('POSTGRES_PASSWORD_EVALUACION')} "
        f"host={get_required_env('POSTGRES_HOST_EVALUACION')} "
        f"port={os.getenv('POSTGRES_PORT_EVALUACION', '5432')}"
    )