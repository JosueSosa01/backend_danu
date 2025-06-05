from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from typing import Optional

app = FastAPI(title="Dashboard Nuevo León")

# CORS para Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== FUNCIONES ==========
def cargar_df(archivo, tipo_centro, semestre):
    df = pd.read_csv(archivo)
    df["tipo_centro"] = tipo_centro
    df["semestre"] = semestre
    return df

# ========== CARGAR ARCHIVOS REALES ==========
df_nuevos_s1 = cargar_df("costos_nuevos_S1.csv", "Nuevos", "Semestre 1")
df_viejos_s1 = cargar_df("costos_viejos_S1.csv", "Viejos", "Semestre 1")
df_nuevos_s2 = cargar_df("Costo_Gasolina_nuevos_S2.csv", "Nuevos", "Semestre 2")
df_viejos_s2 = cargar_df("Costo_Gasolina_viejos_S2.csv", "Viejos", "Semestre 2")

# ========== UNIR TODO ==========
df_costos = pd.concat([df_nuevos_s1, df_viejos_s1, df_nuevos_s2, df_viejos_s2], ignore_index=True)

# Filtrar por estado = "Nuevo León"
df_costos = df_costos[df_costos["estado"] == "Nuevo León"]

# ========== ENDPOINT DE KPIS ==========
@app.get("/kpis")
def get_kpis(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = df_costos.copy()

    if semestre:
        df = df[df["semestre"] == semestre]
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]

    if df.empty:
        return {"error": "No hay datos para el filtro aplicado."}

    return {
        "Kilómetros recorridos": f"{df['km_recorridos'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['costo_promedio_ruta'].mean():,.2f}",
        "Total de rutas": int(df.shape[0])
    }

# ========== GRAFICA CO2 ==========
@app.get("/charts/co2")
def chart_co2(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = df_costos.copy()

    if semestre:
        df = df[df["semestre"] == semestre]
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]

    if df.empty:
        return {"error": "No hay datos"}

    agrupado = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    return agrupado.to_dict(orient="records")

# ========== GRAFICA GASOLINA ==========
@app.get("/charts/gasolina")
def chart_gasolina(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = df_costos.copy()

    if semestre:
        df = df[df["semestre"] == semestre]
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]

    if df.empty:
        return {"error": "No hay datos"}

    agrupado = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
    return agrupado.to_dict(orient="records")

# ========== GRAFICA DISTANCIA ==========
@app.get("/charts/distancia")
def chart_distancia(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = df_costos.copy()

    if semestre:
        df = df[df["semestre"] == semestre]
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]

    if df.empty:
        return {"error": "No hay datos"}

    hist = df["km_recorridos"].value_counts(bins=20).sort_index().reset_index()
    hist.columns = ["rango_km", "frecuencia"]
    hist["rango_km"] = hist["rango_km"].astype(str)

    return hist.to_dict(orient="records")
