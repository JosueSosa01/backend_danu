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

# === Función de eliminación de outliers ===
def quitar_outliers(df: pd.DataFrame, columnas: list) -> pd.DataFrame:
    for col in columnas:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lim_inf = q1 - 1.5 * iqr
        lim_sup = q3 + 1.5 * iqr
        df = df[(df[col] >= lim_inf) & (df[col] <= lim_sup)]
    return df

# === Filtrado con outliers eliminados ===
def aplicar_filtros(df: pd.DataFrame, tipo_centro: Optional[str], centro: Optional[str]) -> pd.DataFrame:
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
        df = quitar_outliers(df, ["distancia_km", "gasto_gasolina", "co2_emitido"])
    if tipo_centro == "Nuevos" and centro and centro != "Todos":
        df = df[df["nombre_centro"] == centro]
    return df

# === KPIs ===
@app.get("/kpis")
def obtener_kpis(tipo_centro: str = Query(...), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos disponibles."})

    return {
        "Kilómetros recorridos": f"{df['distancia_km'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['gasto_gasolina'].mean():,.2f}",
        "Total de rutas": len(df)
    }

# === Gasto gasolina ===
@app.get("/charts/gasolina")
def grafica_gasolina(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
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

# === Emisiones CO₂ ===
@app.get("/charts/co2")
def grafica_co2(tipo_centro: Optional[str] = Query(None), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    resumen = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    return resumen.to_dict(orient="records")

# === Distribución distancia ===
@app.get("/charts/distancia")
def grafica_distancia(tipo_centro: Optional[str] = Query(None), visualizacion: Optional[str] = Query("Agrupadas"), centro: Optional[str] = Query("Todos")):
    df = aplicar_filtros(df_total, tipo_centro, centro)
    if df.empty:
        return JSONResponse(status_code=404, content={"error": "No hay datos."})

    bins = pd.cut(df["distancia_km"], bins=10)
    df["bin"] = bins
    df["distancia_centro"] = df["bin"].apply(lambda r: round((r.left + r.right) / 2))

    if tipo_centro == "Nuevos" and visualizacion == "Desagrupadas":
        resumen = df.groupby(["distancia_centro", "nombre_centro"]).size().reset_index(name="frecuencia")
        resumen = resumen.rename(columns={"nombre_centro": "grupo"})
    else:
        resumen = df.groupby(["distancia_centro", "tipo_centro"]).size().reset_index(name="frecuencia")
        resumen = resumen.rename(columns={"tipo_centro": "grupo"})

    return resumen[["distancia_centro", "grupo", "frecuencia"]].to_dict(orient="records")

# === Centros disponibles ===
@app.get("/centros")
def obtener_centros(tipo_centro: Optional[str] = Query("Nuevos")):
    df = df_total[df_total["tipo_centro"] == tipo_centro]
    if tipo_centro == "Nuevos":
        centros = df["nombre_centro"].dropna().unique().tolist()
    else:
        centros = []
    return {"centros": centros}

# === Promedios ===
def calcular_promedios_generales():
    df_n_sin = quitar_outliers(df_nuevos.copy(), ["distancia_km", "gasto_gasolina", "co2_emitido"])
    df_v_sin = quitar_outliers(df_viejos.copy(), ["distancia_km", "gasto_gasolina", "co2_emitido"])

    return {
        "distancia": {
            "Nuevos": df_n_sin["distancia_km"].mean(),
            "Viejos": df_v_sin["distancia_km"].mean()
        },
        "gasto_gasolina": {
            "Nuevos": df_n_sin.groupby("mes")["gasto_gasolina"].sum().mean(),
            "Viejos": df_v_sin.groupby("mes")["gasto_gasolina"].sum().mean()
        },
        "co2_emitido": {
            "Nuevos": df_n_sin.groupby("mes")["co2_emitido"].sum().mean(),
            "Viejos": df_v_sin.groupby("mes")["co2_emitido"].sum().mean()
        }
    }

@app.get("/charts/promedios")
def obtener_promedios():
    prom = calcular_promedios_generales()
    return {
        "distancia": {k: round(v, 2) for k, v in prom["distancia"].items()},
        "gasto_gasolina": {k: round(v, 2) for k, v in prom["gasto_gasolina"].items()},
        "co2_emitido": {k: round(v, 2) for k, v in prom["co2_emitido"].items()}
    }

