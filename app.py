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

# === Asignar semestre automáticamente según mes ===
def asignar_semestre(df):
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"], errors="coerce")
    df = df[df["fecha_entrega"].notnull()]
    df["semestre"] = df["fecha_entrega"].dt.month.apply(lambda m: "Semestre 1" if 1 <= m <= 6 else "Semestre 2")
    return df

# === Cargar y estandarizar archivos ===
def cargar_df(archivo, tipo_centro, mapping):
    df = pd.read_csv(archivo)
    df.rename(columns=mapping, inplace=True)
    df["tipo_centro"] = tipo_centro
    df = asignar_semestre(df)
    return df[["fecha_entrega", "distancia_km", "gasto_gasolina", "co2_emitido", "tipo_centro", "semestre"]]

# Archivos Semestre 1
df_nuevos_s1 = cargar_df("costos_nuevos_S1.csv", "Nuevos", {
    "emisiones_co2": "co2_emitido",
    "costo_gasolina": "gasto_gasolina",
    "distancia_km": "distancia_km"
})
df_viejos_s1 = cargar_df("costos_viejos_S1.csv", "Viejos", {
    "emisiones_co2": "co2_emitido",
    "costo_gasolina": "gasto_gasolina",
    "distancia_km": "distancia_km"
})

# Archivos Semestre 2
df_nuevos_s2 = cargar_df("Costo_Gasolina_nuevos_S2.csv", "Nuevos", {
    "co2_emitido_kg": "co2_emitido",
    "gasto_gasolina": "gasto_gasolina",
    "distancia_km": "distancia_km"
})
df_viejos_s2 = cargar_df("Costo_Gasolina_viejos_S2.csv", "Viejos", {
    "co2_emitido_kg": "co2_emitido",
    "gasto_gasolina": "gasto_gasolina",
    "distancia_km": "distancia_km"
})

# Concatenar
df_total = pd.concat([df_nuevos_s1, df_viejos_s1, df_nuevos_s2, df_viejos_s2], ignore_index=True)

# === Aplicar filtros ===
def aplicar_filtros(df, semestre: Optional[str], tipo_centro: Optional[str]):
    if semestre:
        df = df[df["semestre"] == semestre]
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
        df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")
        resumen = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
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
        df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")
        resumen = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
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
