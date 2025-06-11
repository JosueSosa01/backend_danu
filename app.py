from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Optional

app = FastAPI(title="Dashboard Nuevo León")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Cargar CSVs ===
df_nuevos = pd.read_csv("costos_nuevos_S1.csv")
df_viejos = pd.read_csv("costos_viejos_S1.csv")

# === Estandarización ===
def estandarizar(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    df = df.copy()
    df["tipo_centro"] = tipo
    df = df.rename(columns={
        "costo_gasolina": "gasto_gasolina",
        "emisiones_co2": "co2_emitido"
    })
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"], format="%d/%m/%y", errors="coerce")
    df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")

    columnas = [
        "fecha_entrega", "mes", "distancia_km", "gasto_gasolina",
        "co2_emitido", "tipo_centro", "grupo_ruta"
    ]
    if tipo == "Nuevos":
        columnas += ["centro", "nombre_centro"]

    return df[columnas].dropna(subset=["fecha_entrega"])

df_nuevos = estandarizar(df_nuevos, "Nuevos")
df_viejos = estandarizar(df_viejos, "Viejos")
df_total = pd.concat([df_nuevos, df_viejos], ignore_index=True)

MESES_VALIDOS = ["Jan 2018", "Feb 2018", "Mar 2018", "Apr 2018", "May 2018", "Jun 2018"]

# === Filtros ===
def aplicar_filtros(df: pd.DataFrame, tipo: Optional[str], centro: Optional[str]) -> pd.DataFrame:
    if tipo:
        df = df[df["tipo_centro"] == tipo]
    if centro and tipo == "Nuevos" and centro != "Todos":
        df = df[df["nombre_centro"] == centro]
    return df[df["mes"].isin(MESES_VALIDOS)].copy()

# === KPIs ===
@app.get("/kpis")
def kpis(tipo_centro: str = Query(...), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    df = df.dropna(subset=["distancia_km", "gasto_gasolina", "co2_emitido"])

    return {
        "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['gasto_gasolina'].mean():,.2f}",
        "Total de rutas": int(len(df))
    }

# === Charts ===
@app.get("/charts/gasolina")
def gasolina(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    if tipo_centro == "Nuevos" and visualizacion == "Desagrupadas":
        resumen = df.groupby(["mes", "nombre_centro"])["gasto_gasolina"].sum().reset_index()
        resumen = resumen.rename(columns={"nombre_centro": "grupo"})
    else:
        resumen = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
        resumen = resumen.rename(columns={"tipo_centro": "grupo"})

    return resumen.to_dict(orient="records")

@app.get("/charts/co2")
def co2(tipo_centro: Optional[str] = Query(None), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    resumen = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    return resumen.to_dict(orient="records")

@app.get("/charts/distancia")
def distancia(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total, tipo_centro, centro)
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

@app.get("/centros")
def obtener_centros(tipo_centro: Optional[str] = Query("Nuevos")):
    df = df_total[df_total["tipo_centro"] == tipo_centro]
    centros = df["nombre_centro"].dropna().unique().tolist() if tipo_centro == "Nuevos" else []
    return {"centros": centros}
