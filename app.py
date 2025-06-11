from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Optional

app = FastAPI(title="Dashboard Nuevo León")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Archivos CSV ===
df_nuevos = pd.read_csv("costos_nuevos_S1.csv")
df_viejos = pd.read_csv("costos_viejos_S1.csv")

# === Estandarización ===
def estandarizar(df, tipo_centro):
    df = df.copy()
    df["tipo_centro"] = tipo_centro
    df.rename(columns={
        "emisiones_co2": "co2_emitido",
        "costo_gasolina": "gasto_gasolina",
        "distancia_km": "distancia_km"
    }, inplace=True)
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"], errors="coerce")
    df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")
    return df[["fecha_entrega", "mes", "distancia_km", "gasto_gasolina", "co2_emitido", "tipo_centro", "grupo_ruta", "centro", "nombre_centro"]].dropna(subset=["fecha_entrega"])

# Unimos ambos
df_total = pd.concat([
    estandarizar(df_nuevos, "Nuevos"),
    estandarizar(df_viejos, "Viejos")
], ignore_index=True)

MESES_SEMESTRE_1 = ["Jan 2018", "Feb 2018", "Mar 2018", "Apr 2018", "May 2018", "Jun 2018"]
df_total = df_total[df_total["mes"].isin(MESES_SEMESTRE_1)]

# === Aplicar filtros ===
def aplicar_filtros(df, tipo_centro=None, centro=None):
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    if centro:
        df = df[df["nombre_centro"] == centro]
    return df

# === KPIs ===
@app.get("/kpis")
def obtener_kpis(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query(None)
):
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

# === Gráfica CO2 ===
@app.get("/charts/co2")
def grafica_co2(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query(None)
):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
        resumen = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
        return resumen.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Gráfica gasolina ===
@app.get("/charts/gasolina")
def grafica_gasolina(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query(None)
):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
        resumen = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
        return resumen.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Gráfica distancia (agrupada o desagrupada) ===
@app.get("/charts/distancia")
def grafica_distancia(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query(None),
    visualizacion: Optional[str] = Query("Agrupadas")  # Agrupadas o Desagrupadas
):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)

        if df.empty:
            return {"error": "Sin datos para este filtro."}

        if visualizacion == "Agrupadas":
            # Agrupar en 10 bins
            hist = df["distancia_km"].value_counts(bins=10).sort_index().reset_index()
            hist.columns = ["rango_km", "frecuencia"]

            def formato_rango(rango):
                return f"{round(rango.left)}–{round(rango.right)} km"

            hist["rango_km"] = hist["rango_km"].apply(formato_rango)
            return hist.to_dict(orient="records")
        else:
            # Desagrupadas por tipo de centro
            bins = pd.cut(df["distancia_km"], bins=10)
            grouped = df.groupby([bins, "tipo_centro"]).size().unstack(fill_value=0)
            grouped = grouped.reset_index().rename(columns={"distancia_km": "rango_km"})

            def formato_rango(rango):
                return f"{round(rango.left)}–{round(rango.right)} km"

            grouped["rango_km"] = grouped["rango_km"].apply(formato_rango)
            return grouped.to_dict(orient="records")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Centros únicos ===
@app.get("/centros")
def listar_centros(tipo_centro: Optional[str] = Query(None)):
    df = aplicar_filtros(df_total.copy(), tipo_centro)
    centros = df["nombre_centro"].dropna().unique().tolist()
    return sorted(centros)

