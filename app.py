from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from typing import Optional

app = FastAPI(title="Dashboard Nuevo León")

# Habilitar CORS para Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Función de carga y estandarización ==========
def cargar_df_s2(archivo, tipo_centro):
    df = pd.read_csv(archivo)
    df["tipo_centro"] = tipo_centro
    df["semestre"] = "Semestre 2"
    df.rename(columns={
        "co2_emitido_kg": "co2_emitido",
        "gasto_gasolina": "gasto_gasolina",
        "distancia_km": "distancia_km"
    }, inplace=True)
    return df[["fecha_entrega", "distancia_km", "gasto_gasolina", "co2_emitido", "tipo_centro", "semestre"]]

def cargar_df_s1(archivo, tipo_centro):
    df = pd.read_csv(archivo)
    df["tipo_centro"] = tipo_centro
    df["semestre"] = "Semestre 1"
    df.rename(columns={
        "emisiones_co2": "co2_emitido",
        "costo_gasolina": "gasto_gasolina",
        "distancia_km": "distancia_km"
    }, inplace=True)
    return df[["fecha_entrega", "distancia_km", "gasto_gasolina", "co2_emitido", "tipo_centro", "semestre"]]

# ========== Carga unificada ==========
df_nuevos_s1 = cargar_df_s1("costos_nuevos_S1.csv", "Nuevos")
df_viejos_s1 = cargar_df_s1("costos_viejos_S1.csv", "Viejos")
df_nuevos_s2 = cargar_df_s2("Costo_Gasolina_nuevos_S2.csv", "Nuevos")
df_viejos_s2 = cargar_df_s2("Costo_Gasolina_viejos_S2.csv", "Viejos")

df_total = pd.concat([df_nuevos_s1, df_viejos_s1, df_nuevos_s2, df_viejos_s2], ignore_index=True)

# ========== Filtro ==========
def aplicar_filtros(df, semestre: Optional[str], tipo_centro: Optional[str]):
    if semestre:
        df = df[df["semestre"] == semestre]
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    return df

# ========== KPIS ==========
@app.get("/kpis")
def obtener_kpis(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)

    if df.empty:
        return {"error": "No hay datos para los filtros aplicados."}

    return {
        "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['gasto_gasolina'].mean():,.2f}",
        "Total de rutas": int(len(df))
    }

# ========== Gráfica de CO2 ==========
@app.get("/charts/co2")
def grafica_co2(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos para este filtro."}

    df["mes"] = pd.to_datetime(df["fecha_entrega"]).dt.strftime("%b %Y")
    resumen = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    return resumen.to_dict(orient="records")

# ========== Gráfica de gasto gasolina ==========
@app.get("/charts/gasolina")
def grafica_gasolina(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos para este filtro."}

    df["mes"] = pd.to_datetime(df["fecha_entrega"]).dt.strftime("%b %Y")
    resumen = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
    return resumen.to_dict(orient="records")

# ========== Histograma de distancias ==========
@app.get("/charts/distancia")
def grafica_distancia(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos para este filtro."}

    hist = df["distancia_km"].value_counts(bins=20).sort_index().reset_index()
    hist.columns = ["rango_km", "frecuencia"]
    hist["rango_km"] = hist["rango_km"].astype(str)
    return hist.to_dict(orient="records")



