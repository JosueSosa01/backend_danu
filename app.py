from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from typing import Optional

# Inicializar app
app = FastAPI(title="Dashboard Nuevo León")

# Habilitar CORS
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

# ========== CARGA DE ARCHIVOS ORIGINALES ==========
df_nuevos_s1 = cargar_df("costos_nuevos_S1.csv", "Nuevos", "Semestre 1")
df_viejos_s1 = cargar_df("costos_viejos_S1.csv", "Viejos", "Semestre 1")
df_nuevos_s2 = cargar_df("Costo_Gasolina_nuevos_S2.csv", "Nuevos", "Semestre 2")
df_viejos_s2 = cargar_df("Costo_Gasolina_viejos_S2.csv", "Viejos", "Semestre 2")

# ========== UNIR TODOS ==========
df_costos = pd.concat([df_nuevos_s1, df_viejos_s1, df_nuevos_s2, df_viejos_s2], ignore_index=True)

# ========== FILTRO GLOBAL ==========
def filtrar(df, semestre: Optional[str], tipo_centro: Optional[str]):
    if semestre:
        df = df[df["semestre"] == semestre]
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    return df

# ========== ENDPOINT DE KPIS ==========
@app.get("/kpis")
def get_kpis(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = filtrar(df_costos.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "No hay datos para los filtros aplicados."}

    return {
        "Kilómetros recorridos": f"{df['km_recorridos'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['costo_promedio_ruta'].mean():,.2f}",
        "Total de rutas": int(len(df))
    }

# ========== GRÁFICA: EMISIONES DE CO2 ==========
@app.get("/charts/co2")
def chart_co2(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = filtrar(df_costos.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos"}

    df_grouped = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    return df_grouped.to_dict(orient="records")

# ========== GRÁFICA: GASTO EN GASOLINA ==========
@app.get("/charts/gasolina")
def chart_gasolina(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = filtrar(df_costos.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos"}

    df_grouped = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
    return df_grouped.to_dict(orient="records")

# ========== GRÁFICA: DISTANCIAS RECORRIDAS ==========
@app.get("/charts/distancia")
def chart_distancia(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = filtrar(df_costos.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos"}

    hist = df["km_recorridos"].value_counts(bins=20).sort_index().reset_index()
    hist.columns = ["rango_km", "frecuencia"]
    hist["rango_km"] = hist["rango_km"].astype(str)

    return hist.to_dict(orient="records")

