import os
import pandas as pd
import glob  # Agregamos glob para escanear la capa Silver dinámicamente
from datetime import datetime  # 💡 Necesario para la marca de tiempo histórica

def procesar_capa_gold():
    print("=== INICIANDO PROCESAMIENTO DE LA CAPA GOLD ===")
    
    # -------------------------------------------------------------------------
    # CONFIGURACIÓN DE RUTAS DINÁMICAS (Capa Silver a Gold)
    # -------------------------------------------------------------------------
    carpeta_silver = "/opt/airflow/data/2_silver"
    carpeta_salida = "/opt/airflow/data/3_gold"
    os.makedirs(carpeta_salida, exist_ok=True)
    
    # 🔍 1. Buscar dinámicamente el último archivo de resoluciones limpias (Se ajustó el patrón a *_ para soportar marcas de tiempo)
    archivos_resoluciones = glob.glob(os.path.join(carpeta_silver, "resoluciones_limpias*.csv"))
    if not archivos_resoluciones:
        raise FileNotFoundError("❌ No se encontró ningún archivo que coincida con 'resoluciones_limpias' en la capa Silver.")
    ruta_silver_resoluciones = max(archivos_resoluciones, key=os.path.getmtime)
    print(f"📂 [CAPA GOLD] Último archivo de Resoluciones detectado: {ruta_silver_resoluciones}")
    
    # 🔍 2. Buscar dinámicamente el último archivo de ubigeo limpio (Se ajustó el patrón a *_ para soportar marcas de tiempo)
    archivos_ubigeo = glob.glob(os.path.join(carpeta_silver, "ubigeo_limpio*.csv"))
    if not archivos_ubigeo:
        raise FileNotFoundError("❌ No se encontró ningún archivo que coincida con 'ubigeo_limpio' en la capa Silver.")
    ruta_silver_ubigeo = max(archivos_ubigeo, key=os.path.getmtime)
    print(f"📂 [CAPA GOLD] Último archivo de Ubigeo detectado: {ruta_silver_ubigeo}")
    
    # 🎯 RUTA DE SALIDA FINAL HISTÓRICA CON TIMESTAMP (Capa Gold)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_salida_gold = os.path.join(carpeta_salida, f"fact_resoluciones_sancionadoras_{timestamp}.csv")

    try:
        # 1. Cargar datos de la capa Silver usando las rutas dinámicas calculadas arriba
        print("\n-> Cargando datos limpios desde la Capa Silver...")
        df_res = pd.read_csv(ruta_silver_resoluciones, sep=';')
        df_ubi = pd.read_csv(ruta_silver_ubigeo, sep=';')
        
        print(f"   Resoluciones cargadas: {len(df_res)} filas.")
        print(f"   Ubigeo cargado: {len(df_ubi)} filas.")

        # 2. Estandarizar llaves de cruce en SUNAFIL (Mayúsculas y sin espacios extras)
        for col in ["Departamento", "Provincia", "Distrito"]:
            if col in df_res.columns:
                df_res[col] = df_res[col].astype(str).str.upper().str.strip()

        # 3. EJECUTAR EL LEFT JOIN (Replicando el Table.NestedJoin de Power Query)
        print("\n-> Ejecutando cruce (Join) entre Resoluciones y Ubigeo...")
        df_gold = pd.merge(
            df_res, 
            df_ubi[['departamento', 'provincia', 'distrito', 'latitude', 'longitude']], 
            left_on=["Departamento", "Provincia", "Distrito"],
            right_on=["departamento", "provincia", "distrito"],
            how="left"
        )
        
        # Eliminar las columnas duplicadas del Ubigeo que se crearon por el cruce en minúsculas
        df_gold = df_gold.drop(columns=["departamento", "provincia", "distrito"])
        print("   ¡Cruce completado con éxito! Coordenadas geográficas integradas.")

        # 4. MIGRACIÓN DE DAX A PYTHON (Columna Calculada)
        print("\n-> Calculando columna de negocio 'Total_Infracciones' (Migrada de DAX)...")
        df_gold['Total_Infracciones'] = (
            df_gold['Monto Total Leves'] + 
            df_gold['Monto Total Graves'] + 
            df_gold['Monto Total Muy Graves']
        )
        print("   Columna 'Total_Infracciones' generada en el origen de datos.")

        #Limpieza columna indeseada
        if "Unnamed: 0" in df_gold.columns: 
            df_gold = df_gold.drop(columns=["Unnamed: 0"])

        # 5. Guardar el producto de datos final para Power BI
        df_gold.to_csv(ruta_salida_gold, index=False, sep=';', encoding="utf-8-sig")
        print(f"\n-> ¡Éxito! Producto analítico guardado en: {ruta_salida_gold}")
        print(f"   Registros finales exportados: {len(df_gold)}")

    except Exception as e:
        print(f"❌ ERROR al procesar la Capa Gold: {str(e)}")
        raise e

    print("\n=== PROCESAMIENTO DE CAPA GOLD FINALIZADO EXITOSAMENTE ===")

if __name__ == "__main__":
    procesar_capa_gold()