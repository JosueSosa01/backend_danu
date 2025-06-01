from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Procesamiento de datos
def cargar_datos():
    df = pd.read_csv("Nacional-BD.csv")
    df_tabla = pd.read_csv("Tabla-Nacional.csv")
    # Generar columnas derivadas si no existen
    if 'dias' not in df.columns:
        df["dias"] = pd.to_datetime(df["fecha_entrega_al_cliente"]).dt.day_name()

    if 'zona' not in df.columns:
        zona_map = {
            "Baja California": "Noroeste", "Baja California Sur": "Noroeste",
            "Chihuahua": "Norte", "Sonora": "Noroeste", "Sinaloa": "Noroeste",
            "Durango": "Norte", "Coahuila": "Norte", "Nuevo León": "Norte", "Tamaulipas": "Norte",
            "Zacatecas": "Norte", "San Luis Potosí": "Centro", "Aguascalientes": "Centro",
            "Jalisco": "Centro", "Guanajuato": "Centro", "Querétaro": "Centro", 
            "Ciudad de México": "Centro", "Edo. de México": "Centro", "Hidalgo": "Centro",
            "Morelos": "Centro", "Tlaxcala": "Centro", "Puebla": "Centro",
            "Michoacán": "Occidente", "Colima": "Occidente", "Nayarit": "Occidente",
            "Veracruz": "Golfo", "Tabasco": "Golfo", "Campeche": "Sureste",
            "Yucatán": "Sureste", "Quintana Roo": "Sureste", "Oaxaca": "Sur",
            "Chiapas": "Sur", "Guerrero": "Sur"
        }
        df["zona"] = df["estado_del_cliente"].map(zona_map).fillna("Otro")

    return df, df_tabla

@app.get("/api/top_productos")
def top_productos():
    df, _ = cargar_datos()
    top = df["categoria_nombre_producto"].value_counts().nlargest(5).reset_index()
    top.columns = ["producto", "cantidad"]
    return top.to_dict(orient="records")

@app.get("/api/por_dia")
def productos_por_dia():
    df, _ = cargar_datos()
    resumen = df["dias"].value_counts().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ).fillna(0).reset_index()
    resumen.columns = ["dia", "productos_entregados"]
    return resumen.to_dict(orient="records")

@app.get("/api/por_zona")
def por_zona():
    df, _ = cargar_datos()
    resumen = df["zona"].value_counts(normalize=True).reset_index()
    resumen.columns = ["zona", "porcentaje"]
    resumen["porcentaje"] = (resumen["porcentaje"] * 100).round(1)
    return resumen.to_dict(orient="records")

@app.get("/api/resumen_tabla")
def resumen_tabla():
    _, df_tabla = cargar_datos()
    columnas = ["estado_del_cliente", "Ordenes", "Tiempo promedio", "Porcentaje a tiempo", "EstadoDesempeño"]
    return df_tabla[columnas].to_dict(orient="records")

@app.get("/api/resumen")
def resumen():
    df, _ = cargar_datos()
    resumen_df = df.groupby("estado_del_cliente")["importe_a_pagar"].sum().reset_index()
    return resumen_df.to_dict(orient="records")

@app.get("/healthz")
def health():
    return {"status": "ok"}