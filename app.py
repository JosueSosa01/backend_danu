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

# === Cargar y estandarizar archivos ===
def cargar_df_s2(archivo, tipo_centro):
    df = pd.read_csv(archivo)
    df["tipo_centro"] = tipo_centro
    df.rename(columns={
        "co2_emitido_kg": "co2_emitido",
        "gasto_gasolina": "gasto_gasolina",
        "distancia_km": "distancia_km"
    }, inplace=True)
    return df[["fecha_entrega", "distancia_km", "gasto_gasolina", "co2_emitido", "tipo_centro"]]

def cargar_df_s1(archivo, tipo_centro):
    df = pd.read_csv(archivo)
    df["tipo_centro"] = tipo_centro
    df.rename(columns={
        "emisiones_co2": "co2_emitido",
        "costo_gasolina": "gasto_gasolina",
        "distancia_km": "distancia_km"
    }, inplace=True)
    return df[["fecha_entrega", "distancia_km", "gasto_gasolina", "co2_emitido", "tipo_centro"]]

# === Cargar todos los archivos CSV ===
df_nuevos_s1 = cargar_df_s1("costos_nuevos_S1.csv", "Nuevos")
df_viejos_s1 = cargar_df_s1("costos_viejos_S1.csv", "Viejos")
df_nuevos_s2 = cargar_df_s2("Costo_Gasolina_nuevos_S2.csv", "Nuevos")
df_viejos_s2 = cargar_df_s2("Costo_Gasolina_viejos_S2.csv", "Viejos")

df_total = pd.concat([df_nuevos_s1, df_viejos_s1, df_nuevos_s2, df_viejos_s2], ignore_index=True)

# === Aplicar filtros ===
def aplicar_filtros(df, semestre: Optional[str], tipo_centro: Optional[str]):
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"], errors="coerce")

    if semestre:
        if semestre == "Semestre 1":
            df = df[df["fecha_entrega"].dt.month <= 6]
        elif semestre == "Semestre 2":
            df = df[df["fecha_entrega"].dt.month >= 7]

    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]

    return df

# === KPIS ===
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

# === GRÁFICA: Emisiones de CO₂ ===
@app.get("/charts/co2")
def grafica_co2(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    try:
        df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
        df = df[df["fecha_entrega"].notnull()]
        df["mes"] = df["fecha_entrega"].dt.to_period("M").dt.to_timestamp()
        resumen = df.groupby([df["mes"], "tipo_centro"])["co2_emitido"].sum().reset_index()
        resumen["mes"] = resumen["mes"].dt.strftime("%b %Y")
        return resumen.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === GRÁFICA: Gasto en gasolina ===
@app.get("/charts/gasolina")
def grafica_gasolina(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    try:
        df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
        df = df[df["fecha_entrega"].notnull()]
        df["mes"] = df["fecha_entrega"].dt.to_period("M").dt.to_timestamp()
        resumen = df.groupby([df["mes"], "tipo_centro"])["gasto_gasolina"].sum().reset_index()
        resumen["mes"] = resumen["mes"].dt.strftime("%b %Y")
        return resumen.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === GRÁFICA: Distribución de distancias recorridas ===
@app.get("/charts/distancia")
def grafica_distancia(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    try:
        df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
        if df.empty:
            return {"error": "Sin datos para este filtro."}
        hist = df["distancia_km"].value_counts(bins=20).sort_index().reset_index()
        hist.columns = ["rango_km", "frecuencia"]
        hist["rango_km"] = hist["rango_km"].astype(str)
        return hist.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

