from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Función de carga y procesamiento de datos
def procesar_datos():
    df = pd.read_csv("Nacional-BD.csv")
    df_tabla = pd.read_csv("Tabla-Nacional.csv")
    # Aquí puedes insertar más procesamiento si lo deseas
    return df, df_tabla

@app.get("/api/resumen")
def resumen():
    try:
        df, _ = procesar_datos()
        resumen_df = df.groupby("estado_del_cliente")["importe_a_pagar"].sum().reset_index()
        return resumen_df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@app.get("/healthz")
def health_check():
    return {"status": "ok"}