import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración Premium
st.set_page_config(page_title="DIMAQUINAS C.A. - CONTROL DE OBRA", layout="wide", page_icon="🏗️")

# Estilos CSS
st.markdown("""
    <style>
    .stMetric { border: 1px solid #1e3a8a; padding: 20px; border-radius: 12px; background: #f8fafc; }
    .header-box { background-color: #1e3a8a; color: white; padding: 20px; border-radius: 10px; margin-bottom: 25px; text-align: center; }
    .title-text { font-size: 32px; font-weight: bold; margin: 0; }
    html, body, [class*="st-"] { color: #000000; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    try:
        df = pd.read_csv("DIMAQUINAS CALLE DOS OJOS.csv")
        df['FECHA'] = pd.to_datetime(df['FECHA'])
        cols_fin = ['MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN']
        for col in cols_fin:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return None

df = load_all_data()

if df is not None:
    # --- DATOS ---
    empresa = df['EMPRESA'].iloc[0] if 'EMPRESA' in df.columns else "DIMAQUINAS C.A."
    obra = df['OBRA'].iloc[0] if 'OBRA' in df.columns else "CALLE DOS OJOS"
    pct_admin = df['% ADMIN'].max()
    df_gastos = df[df['CLASE'] == 'GASTO'].copy()
    
    total_ing = df[df['CLASE'] == 'INGRESO']['MONTO BASE USD'].sum()
    total_neto = df_gastos['MONTO BASE USD'].sum()
    total_honorarios = df_gastos['HONORARIOS'].sum()
    total_pagado = (df_gastos['MONTO PAGADO'].sum()) * (1 + pct_admin/100) if pct_admin > 0 else df_gastos['MONTO PAGADO'].sum()
    saldo = total_ing - total_pagado

    # --- ENCABEZADO ---
    st.markdown(f'<div class="header-box"><p class="title-text">{empresa}<br><span style="font-size:20px;">OBRA: {obra}</span></p></div>', unsafe_allow_html=True)

    # --- MÉTRICAS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL INGRESOS", f"$ {total_ing:,.0f}")
    m2.metric("COSTO NETO OBRA", f"$ {total_neto:,.0f}")
    m3.metric("ADMIN. DELEGADA", f"$ {total_honorarios:,.0f}")
    m4.metric("SALDO DISPONIBLE", f"$ {saldo:,.0f}")

    st.divider()

    # --- PESTAÑAS ---
    t1, t2, t3, t4 = st.tabs(["📊 ANÁLISIS DE GRÁFICOS", "💸 LISTA DE EGRESOS", "💰 LISTA DE INGRESOS", "🔍 BUSCADOR"])

    with t1:
        # Función para estilo de gráfico con texto afuera
        def update_style_final(fig):
            fig.update_layout(
                coloraxis_showscale=False,
                font=dict(color="#000000", size=14),
                yaxis=dict(tickfont=dict(size=14, color="#000000")),
                xaxis=dict(showticklabels=False, range=[0, df_gastos['MONTO BASE USD'].sum() * 1.1]),
                margin=dict(l=50, r=50, t=50, b=50)
            )
            # Texto fuera de la barra para visibilidad total
            fig.update_traces(textposition='outside', textfont=dict(color="black", size=15, family="Arial Black"))
            return fig

        # --- GRÁFICO 1: CATEGORÍAS ---
        st.write("### 📌 Inversión por Categoría (Incluye Admin)")
        df_tipo = df_gastos.groupby('TIPO')['MONTO BASE USD'].sum().reset_index()
        # Inyectar Admin Delegada
        df_tipo = pd.concat([df_tipo, pd.DataFrame({'TIPO': ['ADMIN. DELEGADA'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        df_tipo = df_tipo.sort_values('MONTO BASE USD', ascending=True)
        
        fig_tipo = px.bar(df_tipo, x='MONTO BASE USD', y='TIPO', orientation='h',
                          color='MONTO BASE USD', color_continuous_scale='Viridis', text_auto=',.0f')
        st.plotly_chart(update_style_final(fig_tipo), use_container_width=True)
        
        st.divider()

        # --- GRÁFICO 2: ÁREA DE OBRA ---
        st.write("### 📐 Inversión por Área de Obra (Incluye Admin)")
        df_area = df_gastos.groupby('AREA')['MONTO BASE USD'].sum().reset_index()
        # Inyectar Admin Delegada
        df_area = pd.concat([df_area, pd.DataFrame({'AREA': ['ADMIN. DELEGADA'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        df_area = df_area.sort_values('MONTO BASE USD', ascending=True)
        
        fig_area = px.bar(df_area, x='MONTO BASE USD', y='AREA', orientation='h',
                          color='MONTO BASE USD', color_continuous_scale='Blues', text_auto=',.0f', height=800) 
        st.plotly_chart(update_style_final(fig_area), use_container_width=True)

        st.divider()

        # --- GRÁFICO 3: PROVEEDORES ---
        st.write("### 👥 Inversión por Proveedor (Top 20 + Admin)")
        df_prov = df_gastos.groupby('PROVEEDOR')['MONTO BASE USD'].sum().sort_values(ascending=False).head(20).reset_index()
        # Inyectar Admin Delegada como DIMAQUINAS
        df_prov = pd.concat([df_prov, pd.DataFrame({'PROVEEDOR': [f'{empresa} (ADMIN)'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        df_prov = df_prov.sort_values('MONTO BASE USD', ascending=True)
        
        fig_prov = px.bar(df_prov, x='MONTO BASE USD', y='PROVEEDOR', orientation='h',
                          color='MONTO BASE USD', color_continuous_scale='Reds', text_auto=',.0f', height=800)
        st.plotly_chart(update_style_final(fig_prov), use_container_width=True)

    with t2:
        st.subheader("📝 Listado de Egresos")
        df_egresos_disp = df_gastos[['FECHA', 'TIPO', 'PROVEEDOR', 'DESCRIPCION', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL']].sort_values('FECHA', ascending=False)
        st.dataframe(df_egresos_disp.style.format({
            "MONTO BASE USD": "${:,.0f}", "HONORARIOS": "${:,.0f}", "COSTO TOTAL": "${:,.0f}"
        }), use_container_width=True)

    with t3:
        st.subheader("📥 Listado de Ingresos")
        st.dataframe(df[df['CLASE'] == 'INGRESO'][['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONTO BASE USD']].sort_values('FECHA', ascending=False).style.format({
            "MONTO BASE USD": "${:,.0f}"
        }), use_container_width=True)

    with t4:
        query = st.text_input("Filtrar datos:")
        if query:
            res = df[df.apply(lambda r: r.astype(str).str.contains(query, case=False).any(), axis=1)]
            st.dataframe(res.style.format({"MONTO BASE USD": "${:,.0f}"}), use_container_width=True)

else:
    st.error("Archivo CSV no encontrado.")
