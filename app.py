from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import pandas as pd

app = FastAPI(title="Dashboard Nuevo León")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======= CARGAR CSV ========
df_nuevos = pd.read_csv("costos_nuevos_S1.csv")
df_viejos = pd.read_csv("costos_viejos_S1.csv")

# Estándar común
def estandarizar(df, tipo_centro):
    df["tipo_centro"] = tipo_centro
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"], dayfirst=True, errors="coerce")
    df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")
    return df

df_nuevos = estandarizar(df_nuevos, "Nuevos")
df_viejos = estandarizar(df_viejos, "Viejos")

df_total = pd.concat([df_nuevos, df_viejos], ignore_index=True)

MESES_SEMESTRE_1 = ["Jan 2018", "Feb 2018", "Mar 2018", "Apr 2018", "May 2018", "Jun 2018"]

# ========= FILTROS =========
def aplicar_filtros(df, tipo_centro=None, centro=None):
    df = df[df["mes"].isin(MESES_SEMESTRE_1)]
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    if centro and "centro" in df.columns:
        df = df[df["centro"] == centro]
    return df

# ========= ENDPOINT: KPIS =========
@app.get("/kpis")
def obtener_kpis(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query(None)
):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
        if df.empty:
            return {"error": "No hay datos con esos filtros."}
        return {
            "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
            "Emisiones de CO₂": f"{df['emisiones_co2'].sum():,.0f} kg",
            "Gasto estimado en gasolina": f"${df['costo_gasolina'].sum():,.0f}",
            "Costo promedio por ruta": f"${df['costo_gasolina'].mean():,.2f}",
            "Total de rutas": int(len(df))
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ========= ENDPOINT: CO2 =========
@app.get("/charts/co2")
def grafica_co2(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query(None)
):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
        df = df[df["mes"].notna()]
        resumen = df.groupby(["mes", "tipo_centro"])["emisiones_co2"].sum().reset_index()
        resumen.rename(columns={"emisiones_co2": "co2_emitido"}, inplace=True)
        return resumen.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ========= ENDPOINT: GASOLINA =========
@app.get("/charts/gasolina")
def grafica_gasolina(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query(None),
    visualizacion: Optional[str] = Query("agrupadas")
):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)

        if tipo_centro == "Nuevos" and visualizacion == "desagrupadas":
            resumen = df.groupby(["mes", "nombre_centro"])["costo_gasolina"].sum().reset_index()
            resumen.rename(columns={"nombre_centro": "centro"}, inplace=True)
        else:
            resumen = df.groupby(["mes", "tipo_centro"])["costo_gasolina"].sum().reset_index()
            resumen.rename(columns={"tipo_centro": "centro"}, inplace=True)

        resumen.rename(columns={"costo_gasolina": "gasto_gasolina"}, inplace=True)
        return resumen.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ========= ENDPOINT: DISTANCIA =========
@app.get("/charts/distancia")
def grafica_distancia(
    tipo_centro: Optional[str] = Query(None),
    centro: Optional[str] = Query(None),
    visualizacion: Optional[str] = Query("agrupadas")
):
    try:
        df = aplicar_filtros(df_total.copy(), tipo_centro, centro)

        if df.empty:
            return []

        if tipo_centro == "Nuevos" and visualizacion == "desagrupadas":
            if "nombre_centro" not in df.columns:
                return []
            resultados = []
            for nombre, subdf in df.groupby("nombre_centro"):
                hist = subdf["distancia_km"].value_counts(bins=10).sort_index().reset_index()
                hist.columns = ["rango_km", "frecuencia"]
                hist["centro"] = nombre
                hist["rango_km"] = hist["rango_km"].apply(lambda r: f"{int(r.left)}–{int(r.right)} km")
                resultados.extend(hist.to_dict(orient="records"))
            return resultados
        else:
            hist = df["distancia_km"].value_counts(bins=10).sort_index().reset_index()
            hist.columns = ["rango_km", "frecuencia"]
            hist["centro"] = df["tipo_centro"].iloc[0] if tipo_centro else "Todos"
            hist["rango_km"] = hist["rango_km"].apply(lambda r: f"{int(r.left)}–{int(r.right)} km")
            return hist.to_dict(orient="records")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

