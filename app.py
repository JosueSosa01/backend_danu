from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Optional

app = FastAPI(title="Dashboard Nuevo León")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Cargar archivos CSV originales ===
df_nuevos = pd.read_csv("costos_nuevos_S1.csv")
df_viejos = pd.read_csv("costos_viejos_S1.csv")

# === Estandarizar columnas ===
def estandarizar(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    df = df.copy()
    df["tipo_centro"] = tipo

    df = df.rename(columns={
        "costo_gasolina": "gasto_gasolina",
        "emisiones_co2": "co2_emitido"
    })

    # 🛠 Parseo seguro de fecha
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"], format="%d/%m/%y", errors="coerce")

    # 🧮 Convertir a numérico explícito
    for col in ["distancia_km", "gasto_gasolina", "co2_emitido"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Crear columna mes
    df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")

    # Mostrar log
    total = len(df)
    fechas_ok = df["fecha_entrega"].notnull().sum()
    print(f"{tipo}: {fechas_ok}/{total} fechas válidas")

    columnas_comunes = [
        "fecha_entrega", "mes", "distancia_km", "gasto_gasolina",
        "co2_emitido", "tipo_centro", "grupo_ruta"
    ]

    if tipo == "Nuevos":
        columnas_comunes += ["centro", "nombre_centro"]

    return df[columnas_comunes].dropna(subset=["fecha_entrega"])

# Aplicar limpieza
df_nuevos = estandarizar(df_nuevos, "Nuevos")
df_viejos = estandarizar(df_viejos, "Viejos")

# Unificar datasets
df_total = pd.concat([df_nuevos, df_viejos], ignore_index=True)

# Meses válidos para gráficos
MESES_VALIDOS = ["Jan 2018", "Feb 2018", "Mar 2018", "Apr 2018", "May 2018", "Jun 2018"]

# === Filtros ===
def aplicar_filtros(df: pd.DataFrame, tipo_centro: Optional[str], centro: Optional[str]) -> pd.DataFrame:
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    if centro and tipo_centro == "Nuevos" and centro != "Todos":
        df = df[df["nombre_centro"] == centro]
    return df.copy()

# === KPIs ===
@app.get("/kpis")
def obtener_kpis(
    tipo_centro: str = Query(...),
    centro: Optional[str] = Query("Todos")
):
    df = aplicar_filtros(df_total, tipo_centro, centro)

    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos disponibles."})

    return {
        "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['gasto_gasolina'].mean():,.2f}",
        "Total de rutas": int(len(df))
    }

# === Gasto gasolina ===
@app.get("/charts/gasolina")
def grafica_gasolina(
    tipo_centro: Optional[str] = Query(None),
    visualizacion: Optional[str] = Query("Agrupadas"),
    centro: Optional[str] = Query("Todos")
):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    df = df[df["mes"].isin(MESES_VALIDOS)]

    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    if tipo_centro == "Nuevos" and visualizacion == "Desagrupadas":
        resumen = df.groupby(["mes", "nombre_centro"])["gasto_gasolina"].sum().reset_index()
        resumen = resumen.rename(columns={"nombre_centro": "grupo"})
    else:
        resumen = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
        resumen = resumen.rename(columns={"tipo_centro": "grupo"})

    return resumen.to_dict(orient="records")

# === Emisiones CO₂ ===
@app.get("/charts/co2")
def grafica_co2(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query("Todos")
):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    df = df[df["mes"].isin(MESES_VALIDOS)]

    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    resumen = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    return resumen.to_dict(orient="records")

# === Distribución distancia ===
@app.get("/charts/distancia")
def grafica_distancia(
    tipo_centro: Optional[str] = Query(None),
    visualizacion: Optional[str] = Query("Agrupadas"),
    centro: Optional[str] = Query("Todos")
):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    df = df[df["mes"].isin(MESES_VALIDOS)]

    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    try:
        bins = pd.cut(df["distancia_km"], bins=10)

        if tipo_centro == "Nuevos" and visualizacion == "Desagrupadas":
            resumen = df.groupby([bins, "nombre_centro"]).size().reset_index(name="frecuencia")
            resumen["rango_km"] = resumen["distancia_km"].apply(lambda r: f"{round(r.left)}–{round(r.right)} km")
            resumen = resumen.rename(columns={"nombre_centro": "grupo"})
        else:
            resumen = df.groupby([bins]).size().reset_index(name="frecuencia")
            resumen["rango_km"] = resumen["distancia_km"].apply(lambda r: f"{round(r.left)}–{round(r.right)} km")
            resumen["grupo"] = "Total"

        return resumen[["rango_km", "grupo", "frecuencia"]].to_dict(orient="records")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Centros disponibles ===
@app.get("/centros")
def obtener_centros(tipo_centro: Optional[str] = Query("Nuevos")):
    try:
        df = df_total[df_total["tipo_centro"] == tipo_centro]

        if tipo_centro == "Nuevos" and "nombre_centro" in df.columns:
            centros = df["nombre_centro"].dropna().unique().tolist()
        else:
            centros = []

        return {"centros": centros}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

