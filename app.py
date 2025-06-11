from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Optional

app = FastAPI(title="Dashboard Nuevo León")

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Cargar archivos CSV ===
df_nuevos = pd.read_csv("costos_nuevos_S1.csv")
df_viejos = pd.read_csv("costos_viejos_S1.csv")

# === Procesamiento base ===
def estandarizar_nuevos(df):
    df = df.copy()
    df["tipo_centro"] = "Nuevos"
    df.rename(columns={
        "costo_gasolina": "gasto_gasolina",
        "emisiones_co2": "co2_emitido"
    }, inplace=True)
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"], format="%d/%m/%y", errors="coerce")
    df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")
    return df[[
        "fecha_entrega", "mes", "grupo_ruta", "distancia_km", "total_km",
        "gasto_gasolina", "co2_emitido", "zona", "centro", "nombre_centro", "tipo_centro"
    ]]

def estandarizar_viejos(df):
    df = df.copy()
    df["tipo_centro"] = "Viejos"
    df.rename(columns={
        "costo_gasolina": "gasto_gasolina",
        "emisiones_co2": "co2_emitido"
    }, inplace=True)
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"], format="%d/%m/%y", errors="coerce")
    df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")
    df["zona"] = None
    df["centro"] = None
    df["nombre_centro"] = None
    return df[[
        "fecha_entrega", "mes", "grupo_ruta", "distancia_km", "total_km",
        "gasto_gasolina", "co2_emitido", "zona", "centro", "nombre_centro", "tipo_centro"
    ]]

# === Unir DataFrames ya estandarizados ===
df_total = pd.concat([
    estandarizar_nuevos(df_nuevos),
    estandarizar_viejos(df_viejos)
], ignore_index=True)

# === Constantes ===
MESES_VALIDOS = ["Jan 2018", "Feb 2018", "Mar 2018", "Apr 2018", "May 2018", "Jun 2018"]
df_total = df_total[df_total["mes"].isin(MESES_VALIDOS)]

# === Filtros dinámicos ===
def aplicar_filtros(df, tipo_centro=None, centro=None):
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    if centro and "nombre_centro" in df.columns:
        df = df[df["nombre_centro"] == centro]
    return df

# === ENDPOINTS ===

@app.get("/kpis")
def obtener_kpis(tipo_centro: Optional[str] = None, centro: Optional[str] = None):
    df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
    if df.empty:
        return {"error": "No hay datos para los filtros aplicados."}
    return {
        "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['gasto_gasolina'].mean():,.2f}",
        "Total de rutas": int(len(df))
    }

@app.get("/charts/co2")
def grafica_co2(tipo_centro: Optional[str] = None, centro: Optional[str] = None):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
        resumen = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
        return resumen.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/charts/gasolina")
def grafica_gasolina(tipo_centro: Optional[str] = None, centro: Optional[str] = None):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
        resumen = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
        return resumen.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/charts/distancia")
def grafica_distancia(
    tipo_centro: Optional[str] = None,
    centro: Optional[str] = None,
    visualizacion: Optional[str] = "Agrupadas"
):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
        if df.empty:
            return {"error": "Sin datos para este filtro."}

        if visualizacion == "Desagrupadas":
            bins = pd.cut(df["distancia_km"], bins=10)
            grouped = df.groupby([bins, "tipo_centro"]).size().unstack(fill_value=0)
            grouped = grouped.reset_index()
            grouped["rango_km"] = grouped["distancia_km"].apply(lambda r: f"{round(r.left)}–{round(r.right)} km")
            grouped = grouped.drop(columns=["distancia_km"])
            return grouped.to_dict(orient="records")
        else:
            hist = df["distancia_km"].value_counts(bins=10).sort_index().reset_index()
            hist.columns = ["rango_km", "frecuencia"]
            hist["rango_km"] = hist["rango_km"].apply(lambda r: f"{round(r.left)}–{round(r.right)} km")
            return hist.to_dict(orient="records")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/centros")
def listar_centros(tipo_centro: Optional[str] = None):
    df = aplicar_filtros(df_total.copy(), tipo_centro)
    centros = df["nombre_centro"].dropna().unique().tolist()
    return sorted(centros)

