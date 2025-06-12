from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Optional

app = FastAPI(title="Dashboard Nuevo León")

# === CORS habilitado ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Cargar CSVs ===
def cargar_df(ruta, tipo):
    df = pd.read_csv(ruta, parse_dates=["fecha_entrega"])
    df["tipo_centro"] = tipo
    df["co2_kg"] = df["emisiones_co2"] if "emisiones_co2" in df.columns else df["co2_emitido_kg"]
    df["costo_gasolina"] = df["costo_gasolina"] if "costo_gasolina" in df.columns else df["gasto_gasolina"]
    df["distancia_km"] = df["distancia_km"].clip(lower=1)
    df["mes"] = df["fecha_entrega"].dt.strftime("%b %Y")
    df["centro"] = df["nombre_centro"] if "nombre_centro" in df.columns else df.get("centro", "Sin nombre")
    return df

df_nuevos = cargar_df("costos_nuevos_S1.csv", "Nuevos")
df_viejos = cargar_df("costos_viejos_S1.csv", "Viejos")
df_total = pd.concat([df_nuevos, df_viejos], ignore_index=True)

# === Limpieza de outliers ===
def quitar_outliers(df: pd.DataFrame, col: str):
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lim_inf = q1 - 1.5 * iqr
    lim_sup = q3 + 1.5 * iqr
    return df[(df[col] >= lim_inf) & (df[col] <= lim_sup)]

# === Filtrado ===
def aplicar_filtros(df, tipo_centro: Optional[str], centro: Optional[str]):
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    if tipo_centro == "Nuevos" and centro and centro != "Todos":
        df = df[df["centro"] == centro]
    return df

# === KPIs ===
@app.get("/kpis")
def obtener_kpis(tipo_centro: str = Query(...), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    df_sin_outliers = quitar_outliers(df, "costo_gasolina")
    return {
        "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_kg'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['costo_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df_sin_outliers['costo_gasolina'].mean():,.2f}",
        "Total de rutas": len(df)
    }

# === Gasto gasolina ===
@app.get("/charts/gasolina")
def grafica_gasolina(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
    df = quitar_outliers(df, "costo_gasolina")
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    if tipo_centro == "Nuevos" and visualizacion == "Desagrupadas":
        resumen = df.groupby(["mes", "centro"])["costo_gasolina"].sum().reset_index()
        resumen = resumen.rename(columns={"centro": "grupo", "costo_gasolina": "gasto_gasolina"})
    else:
        resumen = df.groupby(["mes", "tipo_centro"])["costo_gasolina"].sum().reset_index()
        resumen = resumen.rename(columns={"tipo_centro": "grupo", "costo_gasolina": "gasto_gasolina"})

    return resumen.to_dict(orient="records")

# === Emisiones CO2 ===
@app.get("/charts/co2")
def grafica_co2(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
    df = quitar_outliers(df, "co2_kg")
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    resumen = df.groupby(["mes", "tipo_centro"])["co2_kg"].sum().reset_index()
    resumen = resumen.rename(columns={"tipo_centro": "grupo", "co2_kg": "co2_emitido"})
    return resumen.to_dict(orient="records")

# === Distancia ===
@app.get("/charts/distancia")
def grafica_distancia(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total.copy(), tipo_centro, centro)
    df = quitar_outliers(df, "distancia_km")
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    bins = pd.cut(df["distancia_km"], bins=10)
    df["distancia_centro"] = bins.apply(lambda r: round((r.left + r.right) / 2))

    if tipo_centro == "Nuevos" and visualizacion == "Desagrupadas":
        resumen = df.groupby(["distancia_centro", "centro"]).size().reset_index(name="frecuencia")
        resumen = resumen.rename(columns={"centro": "grupo"})
    else:
        resumen = df.groupby(["distancia_centro", "tipo_centro"]).size().reset_index(name="frecuencia")
        resumen = resumen.rename(columns={"tipo_centro": "grupo"})

    return resumen.to_dict(orient="records")

# === Promedios ===
@app.get("/charts/promedios")
def obtener_promedios():
    def limpio(col):
        return quitar_outliers(df_total[[col]].dropna(), col)[col]

    return {
        "distancia": {
            "Nuevos": round(quitar_outliers(df_nuevos, "distancia_km")["distancia_km"].mean(), 2),
            "Viejos": round(quitar_outliers(df_viejos, "distancia_km")["distancia_km"].mean(), 2)
        },
        "gasto_gasolina": {
            "Nuevos": round(quitar_outliers(df_nuevos, "costo_gasolina")["costo_gasolina"].mean(), 2),
            "Viejos": round(quitar_outliers(df_viejos, "costo_gasolina")["costo_gasolina"].mean(), 2)
        },
        "co2_emitido": {
            "Nuevos": round(quitar_outliers(df_nuevos, "co2_kg")["co2_kg"].sum() / 6, 2),
            "Viejos": round(quitar_outliers(df_viejos, "co2_kg")["co2_kg"].sum() / 6, 2)
        }
    }

# === Centros ===
@app.get("/centros")
def obtener_centros(tipo_centro: Optional[str] = Query("Nuevos")):
    df = df_total[df_total["tipo_centro"] == tipo_centro]
    centros = df["centro"].dropna().unique().tolist()
    return {"centros": centros}



