import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Configuración de la página
st.set_page_config(page_title="Control Pro Calle Dos Ojos", layout="wide", page_icon="🏗️")

# Estilo visual mejorado
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eee; }
    h1, h2, h3 { color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        # Cargamos el archivo específico de Calle Dos Ojos
        df = pd.read_csv("DIMAQUINAS CALLE DOS OJOS.csv")
        df['FECHA'] = pd.to_datetime(df['FECHA'])
        
        # Limpieza y conversión de columnas financieras
        cols = ['MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL']
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo CSV: {e}")
        return None

# --- INICIO DE LA APLICACIÓN ---
df = load_data()

if df is not None:
    # --- BARRA LATERAL (Sidebar) ---
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4342/4342728.png", width=80)
    st.sidebar.header("⚙️ Ajustes de Control")
    
    area_m2 = st.sidebar.number_input("Área de Construcción (m²)", value=850.0)
    precio_m2_est = st.sidebar.number_input("Presupuesto Estimado ($/m²)", value=750.0)
    pct_admin = st.sidebar.slider("% Administración Delegada", 0, 20, 10) / 100

    st.sidebar.divider()
    st.sidebar.info("Este dashboard procesa los datos en tiempo real desde el archivo CSV de Calle Dos Ojos.")

    # --- CÁLCULOS GENERALES ---
    # Gastos directos y administración
    df_gastos = df[df['CLASE'] == 'GASTO'].copy()
    df_gastos['HONORARIOS_CALC'] = df_gastos['MONTO BASE USD'] * pct_admin
    df_gastos['TOTAL_CON_ADMIN'] = df_gastos['MONTO BASE USD'] * (1 + pct_admin)
    
    total_ingresos = df[df['CLASE'] == 'INGRESO']['MONTO BASE USD'].sum()
    total_gastos_netos = df_gastos['MONTO BASE USD'].sum()
    total_admin = total_gastos_netos * pct_admin
    total_obra = total_gastos_netos + total_admin
    
    # Pagos y Deudas
    total_pagado = df_gastos['MONTO PAGADO'].sum() * (1 + pct_admin)
    caja_disponible = total_ingresos - total_pagado

    # --- TÍTULO Y MÉTRICAS PRINCIPALES ---
    st.title("🏗️ Control de Obra: Calle Dos Ojos")
    st.subheader("Dimaquinas C.A. - Administración Delegada")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Ingresos", f"${total_ingresos:,.2f}")
    m2.metric("Inversión Total (Obra)", f"${total_obra:,.2f}", f"Admin: ${total_admin:,.0f}")
    m3.metric("Caja Disponible", f"${caja_disponible:,.2f}", delta_color="normal")
    m4.metric("Pagado a la Fecha", f"${total_pagado:,.2f}", delta=f"${total_obra - total_pagado:,.2f} Pendiente", delta_color="inverse")

    st.divider()

    # --- PESTAÑAS DE CONTENIDO ---
    tab1, tab2, tab3 = st.tabs(["📊 Análisis Financiero", "💰 Ingresos y Flujo", "🔍 Buscador Exacto"])

    with tab1:
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.write("### Evolución de Gastos por Disciplina")
            df_area = df_gastos.groupby('AREA')['MONTO BASE USD'].sum().reset_index()
            fig_area = px.pie(df_area, values='MONTO BASE USD', names='AREA', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_area, use_container_width=True)
            
        with c2:
            st.write("### Análisis de m²")
            presupuesto_total = area_m2 * precio_m2_est
            costo_actual_m2 = total_obra / area_m2 if area_m2 > 0 else 0
            
            st.write(f"**Presupuesto Objetivo:** ${presupuesto_total:,.2f}")
            st.write(f"**Costo Real Actual / m²:** ${costo_actual_m2:,.2f}")
            
            progreso = (total_obra / presupuesto_total) if presupuesto_total > 0 else 0
            st.progress(min(progreso, 1.0))
            st.write(f"Ejecución: {progreso*100:.1f}% del presupuesto estimado.")

    with tab2:
        st.write("### Historial de Ingresos")
        df_ing = df[df['CLASE'] == 'INGRESO'][['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONTO BASE USD']].sort_values('FECHA', ascending=False)
        st.dataframe(df_ing, use_container_width=True)
        
        st.write("### Flujo de Caja")
        df_flujo = df.groupby(pd.Grouper(key='FECHA', freq='W'))['MONTO BASE USD'].sum().cumsum()
        st.line_chart(df_flujo)

    with tab3:
        st.write("### 🔍 Buscador de Palabra Exacta")
        st.info("Este buscador solo encontrará la palabra completa. Ejemplo: Si buscas 'Cemento', no aparecerá 'Microcemento'.")
        
        query = st.text_input("Ingresa el material o concepto a buscar (Ej: Cemento):")
        
        if query:
            # Lógica de búsqueda exacta (Case Insensitive)
            pattern = rf'\b{re.escape(query)}\b'
            
            # Buscamos en todas las columnas convirtiendo a string
            mask = df.apply(lambda row: row.astype(str).str.contains(pattern, case=False, regex=True).any(), axis=1)
            df_res = df[mask]
            
            if not df_res.empty:
                st.success(f"Se encontraron {len(df_res)} registros exactos para '{query}'.")
                
                # Cálculo del total de la búsqueda
                total_busc = df_res[df_res['CLASE'] == 'GASTO']['MONTO BASE USD'].sum()
                st.metric(f"Total Neto en '{query}'", f"${total_busc:,.2f}")
                
                st.dataframe(df_res, use_container_width=True)
            else:
                st.warning(f"No se encontraron coincidencias exactas para '{query}'.")
        else:
            st.write("Introduce una palabra arriba para filtrar los datos.")
else:
    st.warning("Por favor, asegura que el archivo 'DIMAQUINAS CALLE DOS OJOS.csv' esté en la misma carpeta.")
