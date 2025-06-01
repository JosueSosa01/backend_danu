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
         # NORTE
            "Baja California": "Norte",
            "Baja California Sur": "Norte",
            "Sonora": "Norte",
            "Sinaloa": "Norte",
            "Chihuahua": "Norte",
            "Coahuila": "Norte",
            "Nuevo León": "Norte",
            "Tamaulipas": "Norte",
            "Durango": "Norte",
            "Zacatecas": "Norte",
            "SLP": "Norte",
            "Aguascalientes": "Norte",
        
            # CENTRO
            "Jalisco": "Centro",
            "Colima": "Centro",
            "Guanajuato": "Centro",
            "Queretaro": "Centro",
            "Hidalgo": "Centro",
            "Ciudad de México": "Centro",
            "Morelos": "Centro",
            "Tlaxcala": "Centro",
            "Puebla": "Centro",
            "Veracruz": "Centro",
        
            # SUR
            "Guerrero": "Sur",
            "Oaxaca": "Sur",
            "Chiapas": "Sur",
            "Tabasco": "Sur",
            "Campeche": "Sur",
            "Yucatán": "Sur",
            "Quintana Roo": "Sur"
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
    _, tabla = cargar_datos()

    tabla['fecha_orden'] = pd.to_datetime(tabla['fecha_orden'], format='%d/%m/%y')
    tabla['fecha_entrega_al_cliente'] = pd.to_datetime(tabla['fecha_entrega_al_cliente'], format='%d/%m/%y')
    tabla['tiempo_entrega_dias'] = (tabla['fecha_entrega_al_cliente'] - tabla['fecha_orden']).dt.days

    resumen = tabla.groupby('estado_del_cliente').agg(
        Ordenes=('order_id', 'count'),
        TiempoPromedio=('tiempo_entrega_dias', 'mean'),
        EntregasATiempo=('estado_de_puntualidad', lambda x: (x == 'A tiempo').sum())
    ).reset_index()

    resumen['PorcentajeATiempo'] = (resumen['EntregasATiempo'] / resumen['Ordenes']) * 100

    def clasificar(p):
        if p >= 95:
            return 'Excellent'
        elif p >= 90:
            return 'Good'
        else:
            return 'Average'

    resumen['EstadoDesempeño'] = resumen['PorcentajeATiempo'].apply(clasificar)
    resumen['Tiempo promedio'] = resumen['TiempoPromedio'].round(1).astype(str) + ' days'
    resumen['Porcentaje a tiempo'] = resumen['PorcentajeATiempo'].round(2).astype(str) + '%'

    tabla_final = resumen[[
        'estado_del_cliente',
        'Ordenes',
        'Tiempo promedio',
        'Porcentaje a tiempo',
        'EstadoDesempeño'
    ]]

    return tabla_final.to_dict(orient="records")

@app.get("/api/resumen")
def resumen():
    df, _ = cargar_datos()
    resumen_df = df.groupby("estado_del_cliente")["importe_a_pagar"].sum().reset_index()
    return resumen_df.to_dict(orient="records")

@app.get("/healthz")
def health():
    return {"status": "ok"}
