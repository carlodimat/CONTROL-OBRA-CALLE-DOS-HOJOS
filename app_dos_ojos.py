import streamlit as st
import pandas as pd
import plotly.express as px
import textwrap

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="DIMAQUINAS C.A. - CONTROL DE OBRA", layout="wide", page_icon="🏗️")

# 2. DISEÑO CSS ADAPTABLE Y CORPORATIVO
st.markdown("""
    <style>
    .stMetric { border: 1px solid #1e3a8a; padding: 15px; border-radius: 12px; background: #f8fafc; }
    .header-box { background-color: #1e3a8a; color: white; padding: 80px 20px; border-radius: 15px; margin-bottom: 30px; text-align: center; }
    
    .title-text { font-weight: 900; margin: 0; text-transform: uppercase; line-height: 1.1; }
    
    @media (max-width: 600px) {
        .title-text { font-size: 35px !important; }
        .subtitle-text { font-size: 18px !important; }
        .header-box { padding: 40px 10px !important; }
    }
    @media (min-width: 601px) {
        .title-text { font-size: 100px; }
        .subtitle-text { font-size: 35px; }
    }
    
    html, body, [class*="st-"] { color: #000000; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# Función para que los nombres largos no empujen el gráfico
def wrap_labels(text, width=15):
    if isinstance(text, str):
        return "<br>".join(textwrap.wrap(text, width=width))
    return text

@st.cache_data
def load_all_data():
    try:
        df = pd.read_csv("DIMAQUINAS CALLE DOS OJOS.csv")
        df['FECHA'] = pd.to_datetime(df['FECHA'])
        cols_fin = ['MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN', 'MONTO ORIG', 'TASA']
        for col in cols_fin:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return None

# --- CARGA DE DATOS ---
df = load_all_data()

if df is not None:
    # --- EXTRACCIÓN DE VARIABLES ---
    empresa = df['EMPRESA'].iloc[0] if 'EMPRESA' in df.columns else "DIMAQUINAS C.A."
    obra = df['OBRA'].iloc[0] if 'OBRA' in df.columns else "CALLE DOS OJOS"
    pct_admin = df['% ADMIN'].max()
    
    df_gastos = df[df['CLASE'] == 'GASTO'].copy()
    df_ingresos = df[df['CLASE'] == 'INGRESO'].copy()
    
    total_ing = df_ingresos['MONTO BASE USD'].sum()
    total_neto = df_gastos['MONTO BASE USD'].sum()
    total_honorarios = df_gastos['HONORARIOS'].sum()
    total_pagado_neto = df_gastos['MONTO PAGADO'].sum()
    total_pagado_real = total_pagado_neto + (total_pagado_neto * (pct_admin/100)) if pct_admin > 0 else total_pagado_neto
    saldo_caja = total_ing - total_pagado_real

    # --- ENCABEZADO MASIVO ---
    st.markdown(f'<div class="header-box"><p class="title-text">{empresa}</p><p class="subtitle-text">OBRA: {obra}</p></div>', unsafe_allow_html=True)

    # --- MÉTRICAS DE RESUMEN ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL INGRESOS", f"$ {total_ing:,.2f}")
    m2.metric("COSTO NETO OBRA", f"$ {total_neto:,.2f}")
    m3.metric("ADMIN. DELEGADA", f"$ {total_honorarios:,.2f}")
    m4.metric("SALDO DISPONIBLE", f"$ {saldo_caja:,.2f}")

    st.divider()

    # --- PESTAÑAS ---
    t1, t2, t3, t4 = st.tabs(["📊 ANÁLISIS DE GRÁFICOS", "💸 LISTA DE EGRESOS", "💰 LISTA DE INGRESOS", "🔍 BUSCADOR"])

    with t1:
        def apply_chart_style(fig, max_val):
            fig.update_layout(
                coloraxis_showscale=False,
                font=dict(color="#000000", size=11),
                yaxis=dict(
                    tickfont=dict(size=11, color="#000000"),
                    categoryorder='total ascending' # FORZAR ORDEN POR MONTO
                ),
                xaxis=dict(showticklabels=False, range=[0, max_val * 1.5]),
                margin=dict(l=10, r=180, t=30, b=10)
            )
            fig.update_traces(textposition='outside', textfont=dict(color="black", size=12, family="Arial Black"))
            return fig

        # 1. Gráfico por Categoría
        st.write("### 📌 Inversión por Categoría (Tipo)")
        df_t = df_gastos.groupby('TIPO')['MONTO BASE USD'].sum().reset_index()
        df_t = pd.concat([df_t, pd.DataFrame({'TIPO':['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD':[total_honorarios]})], ignore_index=True)
        df_t['TIPO'] = df_t['TIPO'].apply(wrap_labels)
        fig1 = px.bar(df_t, x='MONTO BASE USD', y='TIPO', orientation='h', color='MONTO BASE USD', color_continuous_scale='Viridis', text_auto=',.0f')
        st.plotly_chart(apply_chart_style(fig1, df_t['MONTO BASE USD'].max()), use_container_width=True)
        
        st.divider()

        # 2. Gráfico por Área
        st.write("### 📐 Inversión por Área de Obra")
        df_a = df_gastos.groupby('AREA')['MONTO BASE USD'].sum().reset_index()
        df_a = pd.concat([df_a, pd.DataFrame({'AREA':['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD':[total_honorarios]})], ignore_index=True)
        df_a['AREA'] = df_a['AREA'].apply(wrap_labels)
        fig2 = px.bar(df_a, x='MONTO BASE USD', y='AREA', orientation='h', color='MONTO BASE USD', color_continuous_scale='Blues', text_auto=',.0f', height=700)
        st.plotly_chart(apply_chart_style(fig2, df_a['MONTO BASE USD'].max()), use_container_width=True)

        st.divider()

        # 3. Gráfico por Proveedor
        st.write("### 👥 Top Proveedores")
        df_p = df_gastos.groupby('PROVEEDOR')['MONTO BASE USD'].sum().sort_values(ascending=False).head(20).reset_index()
        df_p = pd.concat([df_p, pd.DataFrame({'PROVEEDOR':['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD':[total_honorarios]})], ignore_index=True)
        df_p['PROVEEDOR'] = df_p['PROVEEDOR'].apply(wrap_labels)
        fig3 = px.bar(df_p, x='MONTO BASE USD', y='PROVEEDOR', orientation='h', color='MONTO BASE USD', color_continuous_scale='Reds', text_auto=',.0f', height=800)
        st.plotly_chart(apply_chart_style(fig3, df_p['MONTO BASE USD'].max()), use_container_width=True)

    with t2:
        st.subheader("📝 Listado Detallado de Gastos")
        df_egresos_disp = df_gastos[['FECHA', 'TIPO', 'PROVEEDOR', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL']].sort_values('FECHA', ascending=False)
        st.dataframe(df_egresos_disp.style.format({"MONTO BASE USD": "${:,.2f}", "HONORARIOS": "${:,.2f}", "COSTO TOTAL": "${:,.2f}"}), use_container_width=True)

    with t3:
        st.subheader("💰 Listado de Ingresos")
        st.dataframe(df_ingresos[['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONTO BASE USD']].sort_values('FECHA', ascending=False).style.format({"MONTO BASE USD": "${:,.2f}"}), use_container_width=True)

    with t4:
        st.subheader("🔍 Buscador Inteligente")
        query = st.text_input("Escribe una palabra para filtrar:")
        if query:
            mask = df.apply(lambda r: r.astype(str).str.contains(query, case=False).any(), axis=1)
            res = df[mask]
            st.success(f"Registros: {len(res)} | Total USD: $ {res['MONTO BASE USD'].sum():,.2f}")
            st.dataframe(res.style.format({"MONTO BASE USD": "${:,.2f}", "MONTO ORIG": "{:,.2f}", "TASA": "{:,.2f}", "HONORARIOS": "${:,.2f}", "COSTO TOTAL": "${:,.2f}"}), use_container_width=True)

else:
    st.error("No se encontró el archivo 'DIMAQUINAS CALLE DOS OJOS.csv'")
