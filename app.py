from fastapi import FastAPI
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware

# Inicializa la app
app = FastAPI(title="Dashboard Nuevo León")

# Permitir conexión desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Reemplaza con tu dominio si lo necesitas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Carga de Datos ==========
# Asegúrate que los CSV estén en el mismo directorio o ajusta la ruta
df_rutas = pd.read_csv("rutas.csv")
df_emisiones = pd.read_csv("emisiones.csv")
df_gasolina = pd.read_csv("gasolina.csv")

# Filtrar solo datos de Nuevo León
df_rutas_nl = df_rutas[df_rutas["estado"] == "Nuevo León"]
df_emisiones_nl = df_emisiones[df_emisiones["estado"] == "Nuevo León"]
df_gasolina_nl = df_gasolina[df_gasolina["estado"] == "Nuevo León"]

# ========== Endpoint: KPIs ==========
@app.get("/kpis")
def get_kpis():
    total_km = df_rutas_nl["km"].sum()
    km_reducidos = df_rutas_nl["km_reducidos"].sum()

    emisiones = df_rutas_nl["co2_emitido"].sum()
    co2_ev = df_rutas_nl["co2_ev"].sum()

    gasto_gasolina = df_rutas_nl["gasto_gasolina"].sum()
    ahorro_gasolina = df_rutas_nl["ahorro_gasolina"].sum()

    costo_prom = df_rutas_nl["costo_prom_ruta"].mean()
    ahorro_ruta = df_rutas_nl["ahorro_ruta"].mean()

    total_rutas = df_rutas_nl["ruta_id"].nunique()
    rutas_menos = df_rutas_nl["rutas_menos"].sum()

    return {
        "km_recorridos": f"{total_km:,.0f} km",
        "km_reducidos": f"{km_reducidos:,.0f} km",
        "co2_emitido": f"{emisiones:,.0f} kg",
        "co2_ev": f"{co2_ev:,.0f} kg",
        "gasto_gasolina": f"${gasto_gasolina:,.0f}",
        "ahorro_gasolina": f"${ahorro_gasolina:,.0f}",
        "costo_prom_ruta": f"${costo_prom:,.2f}",
        "ahorro_ruta": f"${ahorro_ruta:,.2f}",
        "total_rutas": int(total_rutas),
        "rutas_menos": int(rutas_menos)
    }

# ========== Endpoint: Gráfica CO₂ por mes ==========
@app.get("/charts/co2")
def chart_emisiones():
    result = df_emisiones_nl.groupby(["mes", "tipo_centro"])["co2_emitido"].sum().reset_index()
    return result.to_dict(orient="records")

# ========== Endpoint: Costo de gasolina por centro ==========
@app.get("/charts/gasolina")
def chart_gasolina():
    result = df_gasolina_nl.groupby(["mes", "tipo_centro"])["costo_gasolina"].sum().reset_index()
    return result.to_dict(orient="records")

# ========== Endpoint: Distribución de distancia recorrida ==========
@app.get("/charts/distancia")
def chart_distancia():
    df_hist = df_rutas_nl["km"].value_counts(bins=20).sort_index().reset_index()
    df_hist.columns = ["rango_km", "frecuencia"]
    df_hist["rango_km"] = df_hist["rango_km"].astype(str)
    return df_hist.to_dict(orient="records")
