from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Optional
import os
import uvicorn

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
    columnas = ["fecha_entrega", "mes", "distancia_km", "gasto_gasolina", "co2_emitido", "tipo_centro", "grupo_ruta"]
    if tipo == "Nuevos":
        columnas += ["centro", "nombre_centro"]
    return df[columnas].dropna(subset=["fecha_entrega"])

df_nuevos = estandarizar(df_nuevos, "Nuevos")
df_viejos = estandarizar(df_viejos, "Viejos")
df_total = pd.concat([df_nuevos, df_viejos], ignore_index=True)

# === Outliers usando percentiles 5%-95% ===
def quitar_outliers(df: pd.DataFrame, columna: str) -> pd.DataFrame:
    q5 = df[columna].quantile(0.05)
    q95 = df[columna].quantile(0.95)
    return df[(df[columna] >= q5) & (df[columna] <= q95)]

# === Filtrado ===
def aplicar_filtros(df: pd.DataFrame, tipo_centro: Optional[str], centro: Optional[str]) -> pd.DataFrame:
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    if tipo_centro == "Nuevos" and centro and centro != "Todos":
        df = df[df["nombre_centro"] == centro]
    return df

# === Endpoint de promedios exactos ===
@app.get("/charts/promedios")
def obtener_promedios():
    def quitar(df: pd.DataFrame, columna: str) -> pd.Series:
        df_filtrado = quitar_outliers(df, columna)
        return df_filtrado[columna]

    return {
        "distancia": {
            "Nuevos": round(quitar(df_nuevos, "distancia_km").mean(), 2),
            "Viejos": round(quitar(df_viejos, "distancia_km").mean(), 2)
        },
        "gasto_gasolina": {
            "Nuevos": round(quitar(df_nuevos, "gasto_gasolina").mean(), 2),
            "Viejos": round(quitar(df_viejos, "gasto_gasolina").mean(), 2)
        },
        "co2_emitido": {
            "Nuevos": round(quitar(df_nuevos, "co2_emitido").mean(), 2),
            "Viejos": round(quitar(df_viejos, "co2_emitido").mean(), 2)
        }
    }

# === KPIs ===
@app.get("/kpis")
def obtener_kpis(tipo_centro: str = Query(...), centro: Optional[str] = Query("Todos")):
    df_filtrado = aplicar_filtros(df_total, tipo_centro, centro)
    if df_filtrado.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos disponibles."})

    df_promedio = quitar_outliers(df_filtrado.copy(), "gasto_gasolina")

    return {
        "Kilómetros recorridos": f"{df_filtrado['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df_filtrado['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df_filtrado['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df_promedio['gasto_gasolina'].mean():,.2f}",
        "Total de rutas": len(df_filtrado)
    }

# === Gráficas ===
@app.get("/charts/gasolina")
def grafica_gasolina(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
    df = df_total.copy() if tipo_centro == "Nuevos" and visualizacion == "Agrupadas" and centro == "Todos" else aplicar_filtros(df_total, tipo_centro, centro)
    df = quitar_outliers(df, "gasto_gasolina")
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    if tipo_centro == "Nuevos" and visualizacion == "Desagrupadas":
        resumen = df.groupby(["mes", "nombre_centro"])["gasto_gasolina"].sum().reset_index()
        resumen = resumen.rename(columns={"nombre_centro": "grupo"})
    else:
        resumen = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
        resumen = resumen.rename(columns={"tipo_centro": "grupo"})
        resumen["grupo"] = resumen["grupo"].replace("Viejos", "Antiguos")

    return resumen.to_dict(orient="records")

@app.get("/charts/co2")
def grafica_co2(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
    df = df_total.copy() if tipo_centro == "Nuevos" and visualizacion == "Agrupadas" and centro == "Todos" else aplicar_filtros(df_total, tipo_centro, centro)
    df = quitar_outliers(df, "co2_emitido")
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    resumen = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    resumen = resumen.rename(columns={"tipo_centro": "grupo"})
    resumen["grupo"] = resumen["grupo"].replace("Viejos", "Antiguos")

    return resumen.to_dict(orient="records")

@app.get("/charts/distancia")
def grafica_distancia(
    tipo_centro: Optional[str] = Query(None),
    visualizacion: Optional[str] = Query("Agrupadas"),
    centro: Optional[str] = Query("Todos")
):
    df = df_total.copy() if tipo_centro == "Nuevos" and visualizacion == "Agrupadas" and centro == "Todos" else aplicar_filtros(df_total, tipo_centro, centro)
    df = quitar_outliers(df, "distancia_km")
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    df = df[df["distancia_km"] <= 600]
    bins = list(range(0, 601, 100))
    df["distancia_centro"] = pd.cut(df["distancia_km"], bins=bins).apply(lambda r: round((r.left + r.right) / 2))

    if tipo_centro == "Nuevos" and visualizacion == "Desagrupadas":
        resumen = df.groupby(["distancia_centro", "nombre_centro"]).size().reset_index(name="frecuencia")
        resumen = resumen.rename(columns={"nombre_centro": "grupo"})
    else:
        resumen = df.groupby(["distancia_centro", "tipo_centro"]).size().reset_index(name="frecuencia")
        resumen = resumen.rename(columns={"tipo_centro": "grupo"})
        resumen["grupo"] = resumen["grupo"].replace("Viejos", "Antiguos")

    return resumen.to_dict(orient="records")

# === Centros ===
@app.get("/centros")
def obtener_centros(tipo_centro: Optional[str] = Query("Nuevos")):
    df = df_total[df_total["tipo_centro"] == tipo_centro]
    centros = df["nombre_centro"].dropna().unique().tolist() if tipo_centro == "Nuevos" else []
    return {"centros": centros}

# === Inicia Uvicorn solo si se ejecuta directamente (Render) ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

