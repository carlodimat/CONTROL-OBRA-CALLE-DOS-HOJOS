import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Configuración Premium
st.set_page_config(page_title="DIMAQUINAS C.A. - CONTROL DE OBRA", layout="wide", page_icon="🏗️")

# Estilos CSS
st.markdown("""
    <style>
    .stMetric { border: 1px solid #1e3a8a; padding: 20px; border-radius: 12px; background: #f8fafc; }
    .header-box { background-color: #1e3a8a; color: white; padding: 20px; border-radius: 10px; margin-bottom: 25px; text-align: center; }
    .title-text { font-size: 32px; font-weight: bold; margin: 0; }
    .subtitle-text { font-size: 18px; opacity: 0.9; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    try:
        df = pd.read_csv("DIMAQUINAS CALLE DOS OJOS.csv")
        df['FECHA'] = pd.to_datetime(df['FECHA'])
        # Limpieza de columnas usando los nombres exactos del CSV
        cols_fin = ['MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN']
        for col in cols_fin:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return None

df = load_all_data()

if df is not None:
    # --- EXTRACCIÓN DE DATOS DINÁMICOS ---
    empresa_nombre = df['EMPRESA'].iloc[0] if 'EMPRESA' in df.columns else "DIMAQUINAS C.A."
    obra_nombre = df['OBRA'].iloc[0] if 'OBRA' in df.columns else "CALLE DOS OJOS"
    pct_admin_real = df['% ADMIN'].max() # Tomamos el porcentaje definido en el archivo

    # --- CÁLCULOS ---
    df_gastos = df[df['CLASE'] == 'GASTO'].copy()
    df_ingresos = df[df['CLASE'] == 'INGRESO'].copy()
    
    total_ing = df_ingresos['MONTO BASE USD'].sum()
    total_gas_neto = df_gastos['MONTO BASE USD'].sum()
    total_honorarios = df_gastos['HONORARIOS'].sum()
    total_obra_con_admin = total_gas_neto + total_honorarios
    
    total_pagado_neto = df_gastos['MONTO PAGADO'].sum()
    # Calculamos el pagado real incluyendo la admin delegada del monto pagado
    total_pagado_con_admin = total_pagado_neto + (total_pagado_neto * (pct_admin_real/100)) if pct_admin_real > 0 else total_pagado_neto
    saldo_disponible = total_ing - total_pagado_con_admin

    # --- ENCABEZADO OFICIAL ---
    st.markdown(f"""
        <div class="header-box">
            <p class="title-text">{empresa_nombre}</p>
            <p class="subtitle-text">CONTROL DE OBRA: {obra_nombre}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- MÉTRICAS PRINCIPALES ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL INGRESOS", f"$ {total_ing:,.2f}")
    m2.metric("COSTO NETO OBRA", f"$ {total_gas_neto:,.2f}")
    m3.metric("ADMIN. DELEGADA", f"$ {total_honorarios:,.2f}", f"{pct_admin_real}% s/neto")
    m4.metric("SALDO EN CAJA", f"$ {saldo_disponible:,.2f}")

    st.divider()

    # --- PESTAÑAS ---
    t1, t2, t3, t4 = st.tabs(["📊 ANÁLISIS DE CATEGORÍAS", "💸 DETALLE DE EGRESOS", "💰 DETALLE DE INGRESOS", "🔍 BUSCADOR"])

    with t1:
        c1, c2 = st.columns(2)
        
        with c1:
            st.write("### 📌 Gastos por Categoría (TIPO)")
            # Agrupamos por la columna TIPO que contiene Mano de Obra, Estructura, etc.
            df_tipo = df_gastos.groupby('TIPO')['MONTO BASE USD'].sum().reset_index()
            if not df_tipo.empty:
                fig_tipo = px.bar(df_tipo, x='TIPO', y='MONTO BASE USD', 
                                  color='TIPO', text_auto=',.2f',
                                  title="Distribución: Mano de Obra, Estructura, Contratistas, etc.")
                fig_tipo.update_layout(showlegend=False)
                st.plotly_chart(fig_tipo, use_container_width=True)
            else:
                st.info("No hay datos de categorías para mostrar.")
            
        with c2:
            st.write("### 👥 Top 10 Proveedores")
            df_prov = df_gastos.groupby('PROVEEDOR')['MONTO BASE USD'].sum().sort_values(ascending=False).head(10).reset_index()
            if not df_prov.empty:
                fig_prov = px.bar(df_prov, x='MONTO BASE USD', y='PROVEEDOR', orientation='h',
                                  color='MONTO BASE USD', color_continuous_scale='Blues')
                fig_prov.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_prov, use_container_width=True)
            else:
                st.info("No hay datos de proveedores para mostrar.")

    with t2:
        st.subheader("📝 Listado de Egresos Detallado")
        df_egresos_disp = df_gastos[['FECHA', 'TIPO', 'PROVEEDOR', 'DESCRIPCION', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL']].sort_values('FECHA', ascending=False)
        st.dataframe(df_egresos_disp.style.format({
            "MONTO BASE USD": "${:,.2f}", 
            "HONORARIOS": "${:,.2f}", 
            "COSTO TOTAL": "${:,.2f}"
        }), use_container_width=True)

    with t3:
        st.subheader("📥 Listado de Ingresos")
        df_ing_disp = df_ingresos[['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONTO BASE USD']].sort_values('FECHA', ascending=False)
        st.dataframe(df_ing_disp.style.format({"MONTO BASE USD": "${:,.2f}"}), use_container_width=True)

    with t4:
        st.subheader("🔍 Buscador de Datos")
        query = st.text_input("Buscar por cualquier palabra (Proveedor, Material, Tipo, etc):")
        if query:
            mask = df.apply(lambda r: r.astype(str).str.contains(query, case=False).any(), axis=1)
            res = df[mask]
            st.success(f"Resultados: {len(res)}")
            st.dataframe(res.style.format({"MONTO BASE USD": "${:,.2f}", "HONORARIOS": "${:,.2f}", "COSTO TOTAL": "${:,.2f}"}), use_container_width=True)
        else:
            st.write("Escribe algo arriba para filtrar...")

else:
    st.error("No se pudo cargar el archivo CSV. Verifica que el nombre sea 'DIMAQUINAS CALLE DOS OJOS.csv'")
