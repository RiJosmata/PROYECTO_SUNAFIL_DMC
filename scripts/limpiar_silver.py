import os
import pandas as pd
import numpy as np
import glob  # Agregamos glob para la búsqueda dinámica
from datetime import datetime  # 💡 Necesario para la marca de tiempo histórica

def procesar_capa_silver():
    print("=== INICIANDO PROCESAMIENTO DE LA CAPA SILVER ===")
    
    # -------------------------------------------------------------------------
    # CONFIGURACIÓN DE RUTAS (Modificado de forma dinámica para Docker)
    # -------------------------------------------------------------------------
    # 1. Definimos la carpeta contenedora en vez de una ruta estática
    carpeta_bronze_input = "/opt/airflow/data/1_bronze"
    
    # 2. Buscamos TODOS los archivos que terminen en .xls en esa carpeta
    archivos_xls = glob.glob(os.path.join(carpeta_bronze_input, "*.xls"))

    if not archivos_xls:
        raise FileNotFoundError("❌ No se encontró ningún archivo .xls en la carpeta /opt/airflow/data/1_bronze/")

    # 3. Ordenamos los archivos por su fecha de modificación para tomar el MÁS RECIENTE
    archivo_mas_reciente = max(archivos_xls, key=os.path.getmtime)

    # 4. Asignamos la variable que tu código ya utiliza abajo
    ruta_bronze = archivo_mas_reciente
    print(f"📂 [CAPA SILVER] Archivo más reciente detectado automáticamente: {ruta_bronze}")
    
    # Modifica la ruta para que apunte directamente a la zona montada por Docker
    ruta_seed_ubigeo = "/opt/airflow/data/seed_data/ubigeo_distrito.csv"
    
    # 🎯 RUTA ABSOLUTA CORRECTA PARA LA SALIDA EN DOCKER (CON TIMESTAMP HISTÓRICO)
    carpeta_salida = "/opt/airflow/data/2_silver"
    os.makedirs(carpeta_salida, exist_ok=True)
    
    # Generamos la marca de tiempo actual para evitar el reemplazo de archivos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_salida_resoluciones = os.path.join(carpeta_salida, f"resoluciones_limpias_{timestamp}.csv")
    ruta_salida_ubigeo = os.path.join(carpeta_salida, f"ubigeo_limpio_{timestamp}.csv")

    # -------------------------------------------------------------------------
    # 1. PROCESAMIENTO DE TABLA: CONSULTA DE RESOLUCIONES (SUNAFIL)
    # -------------------------------------------------------------------------
    print("\n--- Procesando Tabla: Consulta de Resoluciones ---")
    try:
        # Paso 1 y 2 de Power Query: Leer saltando la primera fila vacía (Table.Skip)
        df_res = pd.read_excel(ruta_bronze, skiprows=1)
        print(f"-> Archivo Bronze cargado correctamente. Registros iniciales: {len(df_res)}")
        
        # Paso 3: Quitar la primera columna vacía (Table.RemoveColumns)
        if "Column1" in df_res.columns:
            df_res = df_res.drop(columns=["Column1"])
            print("-> Columna 'Column1' eliminada con éxito.")
        
        # Paso 4: Definir tipos de datos iniciales (Table.TransformColumnTypes)
        columnas_enteros = [
            "Año Expediente Sancionador", "Año de la Resolución Sancionadora", 
            "Código Dependencia", "Código Tipo Resolución", "Código Estado", 
            "Año Acta", "Año Creación Orden"
        ]
        for col in columnas_enteros:
            if col in df_res.columns:
                df_res[col] = df_res[col].astype("Int64")
        
        # Convertir columnas de fecha
        for col in ["Fecha Resolución Sancionador", "Fecha Acta"]:
            if col in df_res.columns:
                df_res[col] = pd.to_datetime(df_res[col], errors='coerce').dt.date

        print("-> Tipos de datos numéricos y fechas estandarizados.")

        # Pasos 5 al 9: Limpieza de montos (Cambiar '.' por ',' y pasar a decimal)
        columnas_montos = [
            "Monto Total Leves", "Monto Total Graves", 
            "Monto Total Muy Graves", "Monto Total de Infracciones"
        ]
        
        for col in columnas_montos:
            if col in df_res.columns:
                df_res[col] = df_res[col].astype(str).str.strip()
                df_res[col] = df_res[col].str.replace(".", "", regex=False) 
                df_res[col] = df_res[col].str.replace(",", ".", regex=False) 
                df_res[col] = pd.to_numeric(df_res[col], errors='coerce')

        # Paso 10: Reemplazar errores/nulos en Monto Total de Infracciones por 0
        df_res["Monto Total de Infracciones"] = df_res["Monto Total de Infracciones"].fillna(0.0)
        print("-> Columnas de montos transformadas a decimales correctamente.")

        # Paso 11: Reemplazar valores nulos en Estado por "DESCONOCIDO"
        if "Estado" in df_res.columns:
            df_res["Estado"] = df_res["Estado"].fillna("DESCONOCIDO")
            print("-> Valores nulos en la columna 'Estado' reemplazados por 'DESCONOCIDO'.")

        # Guardar resultado en la carpeta Silver
        df_res.to_csv(ruta_salida_resoluciones, index=False, sep=';', encoding="utf-8-sig")
        print(f"-> ¡Éxito! Archivo guardado en: {ruta_salida_resoluciones}")

    except Exception as e:
        print(f"❌ ERROR al procesar las Resoluciones de SUNAFIL: {str(e)}")
        raise e

    # -------------------------------------------------------------------------
    # 2. PROCESAMIENTO DE TABLA: UBIGEO (ESTÁTICO / SEED DATA)
    # -------------------------------------------------------------------------
    print("\n--- Procesando Tabla: UBIGEO (Datos Maestros) ---")
    try:
        df_ubi = pd.read_csv(ruta_seed_ubigeo, encoding="latin1", index_col=0)
        print(f"-> Archivo UBIGEO original cargado. Registros: {len(df_ubi)}")

        # Pasos 1 al 4 de UBIGEO: Configurar formatos de coordenadas
        for col in ["latitude", "longitude"]:
            if col in df_ubi.columns:
                df_ubi[col] = df_ubi[col].astype(str).str.strip()
                df_ubi[col] = df_ubi[col].str.replace(",", ".", regex=False)
                df_ubi[col] = pd.to_numeric(df_ubi[col], errors='coerce')
        
        if "inei" in df_ubi.columns:
            df_ubi["inei"] = df_ubi["inei"].astype(str).str.strip()

        # Paso 5: Eliminar columnas innecesarias
        columnas_a_quitar = [
            "indice_vulnerabilidad_alimentaria", "idh_2019", "pct_pobreza_total", 
            "pct_pobreza_extrema", "pob_densidad_2020", "iso_3166_2", "fips", 
            "capital", "superficie", "reniec", "altitude"
        ]
        df_ubi = df_ubi.drop(columns=columnas_a_quitar, errors='ignore')
        print("-> Columnas secundarias eliminadas.")

        # Pasos 6 y 7: Reemplazar valores con error o nulos en latitud y longitud
        df_ubi["latitude"] = df_ubi["latitude"].fillna(-13.435)
        df_ubi["longitude"] = df_ubi["longitude"].fillna(-73.82194444)
        print("-> Valores nulos en coordenadas corregidos con valores por defecto.")

        # Estandarizar textos de ubicación a Mayúsculas
        for col in ["departamento", "provincia", "distrito"]:
            if col in df_ubi.columns:
                df_ubi[col] = df_ubi[col].astype(str).str.upper().str.strip()

        # Guardar resultado en la carpeta Silver
        df_ubi.to_csv(ruta_salida_ubigeo, index=False, sep=';', encoding="utf-8-sig")
        print(f"-> ¡Éxito! Archivo guardado en: {ruta_salida_ubigeo}")

    except Exception as e:
        print(f"❌ ERROR al procesar el archivo de UBIGEO: {str(e)}")
        raise e

    print("\n=== PROCESAMIENTO DE CAPA SILVER FINALIZADO EXITOSAMENTE ===")

if __name__ == "__main__":
    procesar_capa_silver()