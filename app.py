from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

app = FastAPI(title="Dashboard Nuevo León - Separado")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Cargar CSV ===
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
    return df.dropna(subset=["fecha_entrega"])

df_nuevos = estandarizar(df_nuevos, "Nuevos")
df_viejos = estandarizar(df_viejos, "Viejos")

MESES_VALIDOS = ["Jan 2018", "Feb 2018", "Mar 2018", "Apr 2018", "May 2018", "Jun 2018"]

# === NUEVOS ===
@app.get("/kpis/nuevos")
def kpis_nuevos(centro: str = "Todos"):
    df = df_nuevos[df_nuevos["mes"].isin(MESES_VALIDOS)]
    if centro != "Todos":
        df = df[df["nombre_centro"] == centro]
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})
    return {
        "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['gasto_gasolina'].mean():,.2f}",
        "Total de rutas": int(len(df))
    }

@app.get("/charts/gasolina/nuevos")
def gasolina_nuevos():
    df = df_nuevos[df_nuevos["mes"].isin(MESES_VALIDOS)]
    resumen = df.groupby(["mes", "nombre_centro"])["gasto_gasolina"].sum().reset_index()
    resumen = resumen.rename(columns={"nombre_centro": "grupo"})
    return resumen.to_dict(orient="records")

@app.get("/charts/co2/nuevos")
def co2_nuevos():
    df = df_nuevos[df_nuevos["mes"].isin(MESES_VALIDOS)]
    resumen = df.groupby(["mes"])["co2_emitido"].sum().reset_index()
    resumen["tipo_centro"] = "Nuevos"
    return resumen.to_dict(orient="records")

@app.get("/charts/distancia/nuevos")
def distancia_nuevos():
    df = df_nuevos[df_nuevos["mes"].isin(MESES_VALIDOS)]
    bins = pd.cut(df["distancia_km"], bins=10)
    resumen = df.groupby([bins]).size().reset_index(name="frecuencia")
    resumen["rango_km"] = resumen["distancia_km"].apply(lambda r: f"{round(r.left)}–{round(r.right)} km")
    resumen["grupo"] = "Nuevos"
    return resumen[["rango_km", "grupo", "frecuencia"]].to_dict(orient="records")

@app.get("/centros/nuevos")
def centros_nuevos():
    return {"centros": sorted(df_nuevos["nombre_centro"].dropna().unique().tolist())}

# === VIEJOS ===
@app.get("/kpis/viejos")
def kpis_viejos():
    df = df_viejos[df_viejos["mes"].isin(MESES_VALIDOS)]
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})
    return {
        "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['gasto_gasolina'].mean():,.2f}",
        "Total de rutas": int(len(df))
    }

@app.get("/charts/gasolina/viejos")
def gasolina_viejos():
    df = df_viejos[df_viejos["mes"].isin(MESES_VALIDOS)]
    resumen = df.groupby(["mes"])["gasto_gasolina"].sum().reset_index()
    resumen["grupo"] = "Viejos"
    return resumen.to_dict(orient="records")

@app.get("/charts/co2/viejos")
def co2_viejos():
    df = df_viejos[df_viejos["mes"].isin(MESES_VALIDOS)]
    resumen = df.groupby(["mes"])["co2_emitido"].sum().reset_index()
    resumen["tipo_centro"] = "Viejos"
    return resumen.to_dict(orient="records")

@app.get("/charts/distancia/viejos")
def distancia_viejos():
    df = df_viejos[df_viejos["mes"].isin(MESES_VALIDOS)]
    bins = pd.cut(df["distancia_km"], bins=10)
    resumen = df.groupby([bins]).size().reset_index(name="frecuencia")
    resumen["rango_km"] = resumen["distancia_km"].apply(lambda r: f"{round(r.left)}–{round(r.right)} km")
    resumen["grupo"] = "Viejos"
    return resumen[["rango_km", "grupo", "frecuencia"]].to_dict(orient="records")

