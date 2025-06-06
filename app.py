from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from typing import Optional

# Inicializar FastAPI
app = FastAPI(title="Dashboard Nuevo León")

# Activar CORS para permitir acceso desde Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia a tu dominio frontend real si lo necesitas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== FUNCIÓN PARA CARGAR Y NORMALIZAR ==========
def cargar_df(archivo, tipo_centro, semestre):
    df = pd.read_csv(archivo)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["tipo_centro"] = tipo_centro
    df["semestre"] = semestre
    df["centro"] = df["centro"].astype(str)
    return df

# ========== CARGA DE ARCHIVOS DEFINITIVOS ==========
df_nuevos_s1 = cargar_df("costos_nuevos_S1.csv", "Nuevos", "Semestre 1")
df_viejos_s1 = cargar_df("costos_viejos_S1.csv", "Viejos", "Semestre 1")
df_nuevos_s2 = cargar_df("Costo_Gasolina_nuevos_S2.csv", "Nuevos", "Semestre 2")
df_viejos_s2 = cargar_df("Costo_Gasolina_viejos_S2.csv", "Viejos", "Semestre 2")

# ========== UNIR TODOS LOS DATOS ==========
df_total = pd.concat([df_nuevos_s1, df_viejos_s1, df_nuevos_s2, df_viejos_s2], ignore_index=True)

# ========== FILTRO BASE: NUEVO LEÓN ==========
df_total = df_total[df_total["centro"].str.contains("Nuevo León", case=False, na=False)]

# ========== FUNCION DE FILTRADO GLOBAL ==========
def aplicar_filtros(df, semestre: Optional[str], tipo_centro: Optional[str]):
    if semestre:
        df = df[df["semestre"] == semestre]
    if tipo_centro:
        df = df[df["tipo_centro"] == tipo_centro]
    return df

# ========== ENDPOINT PRINCIPAL DE KPIS ==========
@app.get("/kpis")
def obtener_kpis(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)

    if df.empty:
        return {"error": "No hay datos para los filtros aplicados."}

    return {
        "Kilómetros recorridos": f"{df['km_recorridos'].sum():,.0f} km",
        "Emisiones de CO₂": f"{df['co2_emitido'].sum():,.0f} kg",
        "Gasto estimado en gasolina": f"${df['gasto_gasolina'].sum():,.0f}",
        "Costo promedio por ruta": f"${df['costo_promedio_ruta'].mean():,.2f}",
        "Total de rutas": int(len(df))
    }

# ========== GRÁFICA: EMISIONES DE CO₂ ==========
@app.get("/charts/co2")
def grafica_co2(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos"}

    agrupado = df.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    return agrupado.to_dict(orient="records")

# ========== GRÁFICA: GASTO EN GASOLINA ==========
@app.get("/charts/gasolina")
def grafica_gasolina(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos"}

    agrupado = df.groupby(["mes", "tipo_centro"])["gasto_gasolina"].sum().reset_index()
    return agrupado.to_dict(orient="records")

# ========== GRÁFICA: DISTANCIA RECORRIDA ==========
@app.get("/charts/distancia")
def grafica_distancia(
    semestre: Optional[str] = Query(None),
    tipo_centro: Optional[str] = Query(None)
):
    df = aplicar_filtros(df_total.copy(), semestre, tipo_centro)
    if df.empty:
        return {"error": "Sin datos"}

    hist = df["km_recorridos"].value_counts(bins=20).sort_index().reset_index()
    hist.columns = ["rango_km", "frecuencia"]
    hist["rango_km"] = hist["rango_km"].astype(str)
    return hist.to_dict(orient="records")


