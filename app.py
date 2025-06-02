from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import pandas as pd

app = FastAPI()

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Función para cargar y preparar los datos
def cargar_datos():
    df = pd.read_csv("Nacional-BD.csv")
    df_tabla = pd.read_csv("Tabla-Nacional.csv")

    if 'dias' not in df.columns:
        df["fecha_entrega_al_cliente"] = pd.to_datetime(df["fecha_entrega_al_cliente"])
        df["dias"] = df["fecha_entrega_al_cliente"].dt.day_name()

    if 'zona' not in df.columns:
        zona_map = {
            "Baja California": "Norte", "Baja California Sur": "Norte", "Sonora": "Norte",
            "Sinaloa": "Norte", "Chihuahua": "Norte", "Coahuila": "Norte",
            "Nuevo León": "Norte", "Tamaulipas": "Norte", "Durango": "Norte",
            "Zacatecas": "Norte", "SLP": "Norte", "Aguascalientes": "Norte",
            "Jalisco": "Centro", "Colima": "Centro", "Guanajuato": "Centro",
            "Queretaro": "Centro", "Hidalgo": "Centro", "Ciudad de México": "Centro",
            "Morelos": "Centro", "Tlaxcala": "Centro", "Puebla": "Centro",
            "Veracruz": "Centro", "Guerrero": "Sur", "Oaxaca": "Sur", "Chiapas": "Sur",
            "Tabasco": "Sur", "Campeche": "Sur", "Yucatán": "Sur", "Quintana Roo": "Sur"
        }
        df["zona"] = df["estado_del_cliente"].map(zona_map).fillna("Otro")

    return df, df_tabla

# 🔁 Reutilizable: aplica filtros
def aplicar_filtros(df, fecha_inicio, fecha_fin, estados):
    if fecha_inicio and fecha_fin:
        df['fecha_entrega_al_cliente'] = pd.to_datetime(df['fecha_entrega_al_cliente'])
        df = df[(df['fecha_entrega_al_cliente'] >= fecha_inicio) & (df['fecha_entrega_al_cliente'] <= fecha_fin)]
    if estados:
        lista_estados = estados.split(',')
        df = df[df['estado_del_cliente'].isin(lista_estados)]
    return df

@app.get("/api/top_productos")
def top_productos(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    estados: Optional[str] = Query(None)
):
    df, _ = cargar_datos()
    df = aplicar_filtros(df, fecha_inicio, fecha_fin, estados)

    top = df["categoria_nombre_producto"].value_counts().nlargest(5).reset_index()
    top.columns = ["producto", "cantidad"]
    return top.to_dict(orient="records")

@app.get("/api/por_dia")
def productos_por_dia(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    estados: Optional[str] = Query(None)
):
    df, _ = cargar_datos()
    df = aplicar_filtros(df, fecha_inicio, fecha_fin, estados)

    resumen = df["dias"].value_counts().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ).fillna(0).reset_index()
    resumen.columns = ["dia", "productos_entregados"]
    return resumen.to_dict(orient="records")

@app.get("/api/por_zona")
def por_zona(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    df, _ = cargar_datos()
    df = aplicar_filtros(df, fecha_inicio, fecha_fin, None)

    resumen = df["zona"].value_counts(normalize=True).reset_index()
    resumen.columns = ["zona", "porcentaje"]
    resumen["porcentaje"] = (resumen["porcentaje"] * 100).round(1)
    return resumen.to_dict(orient="records")

@app.get("/api/resumen_tabla")
def resumen_tabla(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    estados: Optional[str] = Query(None)
):
    _, tabla = cargar_datos()

    tabla['fecha_orden'] = pd.to_datetime(tabla['fecha_orden'], format='%d/%m/%y')
    tabla['fecha_entrega_al_cliente'] = pd.to_datetime(tabla['fecha_entrega_al_cliente'], format='%d/%m/%y')

    if fecha_inicio and fecha_fin:
        tabla = tabla[(tabla['fecha_entrega_al_cliente'] >= fecha_inicio) & (tabla['fecha_entrega_al_cliente'] <= fecha_fin)]

    if estados:
        lista_estados = estados.split(',')
        tabla = tabla[tabla['estado_del_cliente'].isin(lista_estados)]

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
