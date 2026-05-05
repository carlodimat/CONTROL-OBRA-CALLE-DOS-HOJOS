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

# Función para envolver texto
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

df = load_all_data()

if df is not None:
    # --- VARIABLES INICIALES ---
    empresa = df['EMPRESA'].iloc[0] if 'EMPRESA' in df.columns else "DIMAQUINAS C.A."
    obra = df['OBRA'].iloc[0] if 'OBRA' in df.columns else "CALLE DOS OJOS"
    pct_admin = df['% ADMIN'].max()
    
    df_gastos_base = df[df['CLASE'] == 'GASTO'].copy()
    df_ingresos = df[df['CLASE'] == 'INGRESO'].copy()

    # --- BARRA LATERAL DE FILTROS ---
    st.sidebar.header("🎯 FILTROS DE OBRA")
    
    # Filtro TIPO
    tipos_sel = st.sidebar.multiselect("Filtrar por TIPO:", options=sorted(df_gastos_base['TIPO'].unique()))
    # Filtro AREA
    areas_sel = st.sidebar.multiselect("Filtrar por ÁREA:", options=sorted(df_gastos_base['AREA'].unique()))
    # Filtro PROVEEDOR
    prov_sel = st.sidebar.multiselect("Filtrar por PROVEEDOR:", options=sorted(df_gastos_base['PROVEEDOR'].unique()))

    # Aplicar Filtros
    df_gastos = df_gastos_base.copy()
    if tipos_sel:
        df_gastos = df_gastos[df_gastos['TIPO'].isin(tipos_sel)]
    if areas_sel:
        df_gastos = df_gastos[df_gastos['AREA'].isin(areas_sel)]
    if prov_sel:
        df_gastos = df_gastos[df_gastos['PROVEEDOR'].isin(prov_sel)]

    # --- CÁLCULOS DINÁMICOS ---
    total_ing = df_ingresos['MONTO BASE USD'].sum()
    total_neto = df_gastos['MONTO BASE USD'].sum()
    total_honorarios = df_gastos['HONORARIOS'].sum()
    total_pagado_neto = df_gastos['MONTO PAGADO'].sum()
    # El saldo se calcula sobre el total real, pero las métricas reflejan el filtro
    total_pagado_real = total_pagado_neto + (total_pagado_neto * (pct_admin/100)) if pct_admin > 0 else total_pagado_neto
    saldo_caja = total_ing - total_pagado_real

    # --- ENCABEZADO ---
    st.markdown(f'<div class="header-box"><p class="title-text">{empresa}</p><p class="subtitle-text">OBRA: {obra}</p></div>', unsafe_allow_html=True)

    # --- MÉTRICAS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL INGRESOS", f"$ {total_ing:,.2f}")
    m2.metric("NETO FILTRADO", f"$ {total_neto:,.2f}")
    m3.metric("ADMIN. FILTRADA", f"$ {total_honorarios:,.2f}")
    m4.metric("SALDO CAJA", f"$ {saldo_caja:,.2f}")

    st.divider()

    t1, t2, t3, t4 = st.tabs(["📊 GRÁFICOS", "💸 EGRESOS", "💰 INGRESOS", "🔍 BUSCADOR"])

    with t1:
        def apply_chart_style(fig, max_val):
            fig.update_layout(
                coloraxis_showscale=False,
                font=dict(color="#000000", size=11),
                yaxis=dict(tickfont=dict(size=11, color="#000000"), categoryorder='total ascending'),
                xaxis=dict(showticklabels=False, range=[0, max_val * 1.5]),
                margin=dict(l=10, r=180, t=30, b=10)
            )
            fig.update_traces(textposition='outside', textfont=dict(color="black", size=12, family="Arial Black"))
            return fig

        # 1. Tipo
        st.write("### 📌 Inversión por Tipo")
        df_t = df_gastos.groupby('TIPO')['MONTO BASE USD'].sum().reset_index()
        # Solo inyectar si no hay filtros o si se quiere ver el peso de la admin
        if not tipos_sel:
            df_t = pd.concat([df_t, pd.DataFrame({'TIPO':['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD':[total_honorarios]})], ignore_index=True)
        df_t['TIPO'] = df_t['TIPO'].apply(wrap_labels)
        fig1 = px.bar(df_t, x='MONTO BASE USD', y='TIPO', orientation='h', color='MONTO BASE USD', color_continuous_scale='Viridis', text_auto=',.0f')
        st.plotly_chart(apply_chart_style(fig1, df_t['MONTO BASE USD'].max() if not df_t.empty else 1), use_container_width=True)
        
        st.divider()

        # 2. Área
        st.write("### 📐 Inversión por Área")
        df_a = df_gastos.groupby('AREA')['MONTO BASE USD'].sum().reset_index()
        df_a['AREA'] = df_a['AREA'].apply(wrap_labels)
        fig2 = px.bar(df_a, x='MONTO BASE USD', y='AREA', orientation='h', color='MONTO BASE USD', color_continuous_scale='Blues', text_auto=',.0f', height=700)
        st.plotly_chart(apply_chart_style(fig2, df_a['MONTO BASE USD'].max() if not df_a.empty else 1), use_container_width=True)

        st.divider()

        # 3. Proveedor
        st.write("### 👥 Top Proveedores")
        df_p = df_gastos.groupby('PROVEEDOR')['MONTO BASE USD'].sum().sort_values(ascending=False).head(20).reset_index()
        df_p['PROVEEDOR'] = df_p['PROVEEDOR'].apply(wrap_labels)
        fig3 = px.bar(df_p, x='MONTO BASE USD', y='PROVEEDOR', orientation='h', color='MONTO BASE USD', color_continuous_scale='Reds', text_auto=',.0f', height=800)
        st.plotly_chart(apply_chart_style(fig3, df_p['MONTO BASE USD'].max() if not df_p.empty else 1), use_container_width=True)

    with t2:
        st.subheader("📝 Detalle de Gastos")
        st.dataframe(df_gastos[['FECHA', 'TIPO', 'PROVEEDOR', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL']].sort_values('FECHA', ascending=False).style.format({"MONTO BASE USD": "${:,.2f}", "HONORARIOS": "${:,.2f}", "COSTO TOTAL": "${:,.2f}"}), use_container_width=True)

    with t3:
        st.subheader("💰 Detalle de Ingresos")
        st.dataframe(df_ingresos[['FECHA', 'PROVEEDOR', 'MONTO BASE USD']].sort_values('FECHA', ascending=False).style.format({"MONTO BASE USD": "${:,.2f}"}), use_container_width=True)

    with t4:
        st.subheader("🔍 Buscador")
        q = st.text_input("Filtrar palabra:")
        if q:
            mask = df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)
            res = df[mask]
            st.success(f"Registros: {len(res)} | Total: $ {res['MONTO BASE USD'].sum():,.2f}")
            st.dataframe(res.style.format({"MONTO BASE USD": "${:,.2f}", "MONTO ORIG": "{:,.2f}", "TASA": "{:,.2f}"}), use_container_width=True)
else:
    st.error("No se encontró el archivo CSV.")
