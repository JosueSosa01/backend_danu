from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carga y procesamiento base
def procesar_datos():
    df = pd.read_csv("Nacional-BD.csv")
    df_tabla = pd.read_csv("Tabla-Nacional.csv")
    import pandas as pd
    import numpy as np
    df=pd.read_csv('Nacional-BD.csv')
    df.dtypes
    df['estado_del_cliente'].unique()
    estado_a_zona_general = {
        # NORTE
        "Baja California": "Norte",
        "Baja California Sur": "Norte",
        "Sonora": "Norte",
        "Sinaloa": "Norte",
        "Chihuahua": "Norte",
        "Coahuila": "Norte",
        "Nuevo León": "Norte",
        "Tamaulipas": "Norte",
        "Durango": "Norte",
        "Zacatecas": "Norte",
        "SLP": "Norte",
        "Aguascalientes": "Norte",
        # CENTRO
        "Jalisco": "Centro",
        "Colima": "Centro",
        "Guanajuato": "Centro",
        "Queretaro": "Centro",
        "Hidalgo": "Centro",
        "Ciudad de México": "Centro",
        "Morelos": "Centro",
        "Tlaxcala": "Centro",
        "Puebla": "Centro",
        "Veracruz": "Centro",
        # SUR
        "Guerrero": "Sur",
        "Oaxaca": "Sur",
        "Chiapas": "Sur",
        "Tabasco": "Sur",
        "Campeche": "Sur",
        "Yucatán": "Sur",
        "Quintana Roo": "Sur"
    }
    df["zona"] = df["estado_del_cliente"].map(estado_a_zona_general)
    df['dias'] = pd.to_datetime(df['fecha_entrega_al_cliente']).dt.day_name()
    import plotly.express as px
    zona_counts = df['zona'].value_counts().reset_index()
    zona_counts.columns = ['Zona', 'Cantidad']
    fig = px.pie(
        zona_counts,
        values='Cantidad',
        names='Zona',
        title='Distribución de Órdenes por Zona',
        hole=0.5,
        color_discrete_sequence=['#08306b', '#08519c', '#2171b5', '#4292c6', '#6baed6', '#9ecae1']
    )
    fig.update_traces(
        textinfo='label+percent',
        textposition='outside',
        pull=[0.01] * len(zona_counts)
    )
    fig.update_layout(showlegend=False)
    fig.show()
    import plotly.express as px
    # Obtener el Top 5 de productos más pedidos
    top_productos = df['categoria_nombre_producto'].value_counts().nlargest(5).reset_index()
    top_productos.columns = ['Producto', 'Cantidad']
    # Crear gráfica de barras verticales
    fig = px.bar(
        top_productos,
        x='Producto',
        y='Cantidad',
        title='Top 5 Productos Más Solicitados',
        color='Cantidad',
        color_continuous_scale='Blues'
    )
    # Mostrar los valores encima de las barras
    fig.update_traces(text=top_productos['Cantidad'], textposition='outside')
    # Ajustar layout para mejor apariencia
    fig.update_layout(
        xaxis_title='Producto',
        yaxis_title='Cantidad de Pedidos',
        coloraxis_showscale=False
    )
    fig.show()
    import plotly.express as px
    # Reordenar días de la semana con fill_value por si alguno falta
    productos_por_dia = df['dias'].value_counts().reindex([
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
    ], fill_value=0).reset_index()
    productos_por_dia.columns = ['Dia de la Semana', 'Cantidad']
    # Paleta azul personalizada
    color_list = ['#08306b', '#08519c', '#2171b5', '#4292c6', '#6baed6', '#9ecae1', '#c6dbef']
    # Crear gráfica
    fig = px.bar(
        productos_por_dia,
        x='Dia de la Semana',
        y='Cantidad',
        title='Productos Entregados por Día de la Semana',
        color='Dia de la Semana',
        color_discrete_sequence=color_list,
        text='Cantidad'  # ← Usa los valores reales
    )
    # Colocar texto arriba de cada barra
    fig.update_traces(textposition='outside')
    # Ajustar apariencia
    fig.update_layout(
        xaxis_title='Día de la Semana',
        yaxis_title='Productos Entregados',
        uniformtext_minsize=8,
        uniformtext_mode='show',
        showlegend=False
    )
    fig.show()
    tabla=pd.read_csv('Tabla-Nacional.csv')
    # Convertir fechas a datetime
    tabla['fecha_orden'] = pd.to_datetime(tabla['fecha_orden'], format='%d/%m/%y')
    tabla['fecha_entrega_al_cliente'] = pd.to_datetime(tabla['fecha_entrega_al_cliente'], format='%d/%m/%y')
    # Calcular días de entrega
    tabla['tiempo_entrega_dias'] = (tabla['fecha_entrega_al_cliente'] - tabla['fecha_orden']).dt.days
    # Agrupar por estado
    resumen = tabla.groupby('estado_del_cliente').agg(
        Ordenes=('order_id', 'count'),
        TiempoPromedio=('tiempo_entrega_dias', 'mean'),
        EntregasATiempo=('estado_de_puntualidad', lambda x: (x == 'A tiempo').sum())
    ).reset_index()
    # Calcular porcentaje de entregas a tiempo
    resumen['PorcentajeATiempo'] = (resumen['EntregasATiempo'] / resumen['Ordenes']) * 100
    # Clasificación de desempeño
    def clasificar(p):
        if p >= 95:
            return 'Excellent'
        elif p >= 90:
            return 'Good'
        else:
            return 'Average'
    resumen['EstadoDesempeño'] = resumen['PorcentajeATiempo'].apply(clasificar)
    # Formatear columnas
    resumen['Tiempo promedio'] = resumen['TiempoPromedio'].round(1).astype(str) + ' days'
    resumen['Porcentaje a tiempo'] = resumen['PorcentajeATiempo'].round(2).astype(str) + '%'
    # Seleccionar y renombrar columnas para la tabla final
    tabla = resumen[[
        'estado_del_cliente',
        'Ordenes',
        'Tiempo promedio',
        'Porcentaje a tiempo',
        'EstadoDesempeño'
    ]]
    tabla
    return df, df_tabla

@app.get("/api/resumen")
def resumen():
    try:
        df, _ = procesar_datos()
        resumen_df = df.groupby("estado_del_cliente")["importe_a_pagar"].sum().reset_index()
        return resumen_df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@app.get("/healthz")
def health():
    return {"status": "ok"}