import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración Premium
st.set_page_config(page_title="DIMAQUINAS C.A. - CONTROL DE OBRA", layout="wide", page_icon="🏗️")

# Estilos CSS Adaptables (Mobile First)
st.markdown("""
    <style>
    .stMetric { border: 1px solid #1e3a8a; padding: 15px; border-radius: 12px; background: #f8fafc; }
    .header-box { background-color: #1e3a8a; color: white; padding: 50px 20px; border-radius: 15px; margin-bottom: 30px; text-align: center; }
    
    /* Responsive Title */
    .title-text { font-weight: 900; margin: 0; text-transform: uppercase; line-height: 1.1; }
    
    @media (max-width: 600px) {
        .title-text { font-size: 35px !important; }
        .subtitle-text { font-size: 18px !important; }
        .header-box { padding: 30px 10px !important; }
        .stMetric { padding: 10px !important; }
    }
    @media (min-width: 601px) {
        .title-text { font-size: 100px; }
        .subtitle-text { font-size: 35px; }
    }
    
    html, body, [class*="st-"] { color: #000000; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

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

    # --- ENCABEZADO ADAPTABLE ---
    st.markdown(f"""
        <div class="header-box">
            <p class="title-text">{empresa}</p>
            <p class="subtitle-text">OBRA: {obra}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- MÉTRICAS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL INGRESOS", f"$ {total_ing:,.2f}")
    m2.metric("COSTO NETO", f"$ {total_neto:,.2f}")
    m3.metric("ADMIN.", f"$ {total_honorarios:,.2f}")
    m4.metric("SALDO", f"$ {saldo:,.2f}")

    st.divider()

    t1, t2, t3, t4 = st.tabs(["📊 GRÁFICOS", "💸 EGRESOS", "💰 INGRESOS", "🔍 BUSCADOR"])

    with t1:
        def update_mobile_style(fig, max_val):
            fig.update_layout(
                coloraxis_showscale=False,
                font=dict(color="#000000", size=14),
                yaxis=dict(tickfont=dict(size=14, color="#000000")),
                # Dejar un 40% de margen a la derecha para que los montos no se corten en móvil
                xaxis=dict(showticklabels=False, range=[0, max_val * 1.4]),
                margin=dict(l=10, r=150, t=30, b=10) 
            )
            fig.update_traces(textposition='outside', textfont=dict(color="black", size=14, family="Arial Black"))
            return fig

        # --- CATEGORÍAS ---
        st.write("### 📌 Categorías + Admin")
        df_t = df_gastos.groupby('TIPO')['MONTO BASE USD'].sum().reset_index()
        df_t = pd.concat([df_t, pd.DataFrame({'TIPO':['ADMIN. DELEGADA'], 'MONTO BASE USD':[total_honorarios]})], ignore_index=True)
        df_t = df_t.sort_values('MONTO BASE USD', ascending=True)
        fig1 = px.bar(df_t, x='MONTO BASE USD', y='TIPO', orientation='h', color='MONTO BASE USD', color_continuous_scale='Viridis', text_auto=',.0f')
        st.plotly_chart(update_mobile_style(fig1, df_t['MONTO BASE USD'].max()), use_container_width=True)
        
        st.divider()

        # --- ÁREAS ---
        st.write("### 📐 Áreas + Admin")
        df_a = df_gastos.groupby('AREA')['MONTO BASE USD'].sum().reset_index()
        df_a = pd.concat([df_a, pd.DataFrame({'AREA':['ADMIN. DELEGADA'], 'MONTO BASE USD':[total_honorarios]})], ignore_index=True)
        df_a = df_a.sort_values('MONTO BASE USD', ascending=True)
        fig2 = px.bar(df_a, x='MONTO BASE USD', y='AREA', orientation='h', color='MONTO BASE USD', color_continuous_scale='Blues', text_auto=',.0f', height=700)
        st.plotly_chart(update_mobile_style(fig2, df_a['MONTO BASE USD'].max()), use_container_width=True)

        st.divider()

        # --- PROVEEDORES ---
        st.write("### 👥 Top Proveedores + Admin")
        df_p = df_gastos.groupby('PROVEEDOR')['MONTO BASE USD'].sum().sort_values(ascending=False).head(20).reset_index()
        df_p = pd.concat([df_p, pd.DataFrame({'PROVEEDOR':[f'ADMIN'], 'MONTO BASE USD':[total_honorarios]})], ignore_index=True)
        df_p = df_p.sort_values('MONTO BASE USD', ascending=True)
        fig3 = px.bar(df_p, x='MONTO BASE USD', y='PROVEEDOR', orientation='h', color='MONTO BASE USD', color_continuous_scale='Reds', text_auto=',.0f', height=800)
        st.plotly_chart(update_mobile_style(fig3, df_p['MONTO BASE USD'].max()), use_container_width=True)

    with t2:
        st.subheader("📝 Listado de Egresos Detallado")
        df_egresos_disp = df_gastos[['FECHA', 'TIPO', 'PROVEEDOR', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL']].sort_values('FECHA', ascending=False)
        st.dataframe(df_egresos_disp.style.format({"MONTO BASE USD": "${:,.2f}", "HONORARIOS": "${:,.2f}", "COSTO TOTAL": "${:,.2f}"}), use_container_width=True)

    with t3:
        st.subheader("📥 Listado de Ingresos")
        st.dataframe(df[df['CLASE'] == 'INGRESO'][['FECHA', 'PROVEEDOR', 'MONTO BASE USD']].sort_values('FECHA', ascending=False).style.format({"MONTO BASE USD": "${:,.2f}"}), use_container_width=True)

    with t4:
        st.subheader("🔍 Buscador de Datos")
        query = st.text_input("Filtrar datos por palabra:")
        if query:
            mask = df.apply(lambda r: r.astype(str).str.contains(query, case=False).any(), axis=1)
            res = df[mask]
            st.success(f"Se encontraron **{len(res)}** registros.")
            suma_busc = res['MONTO BASE USD'].sum()
            st.info(f"Suma Total: **$ {suma_busc:,.2f}**")
            st.dataframe(res.style.format({"MONTO BASE USD": "${:,.2f}", "MONTO ORIG": "{:,.2f}", "TASA": "{:,.2f}", "HONORARIOS": "${:,.2f}", "COSTO TOTAL": "${:,.2f}"}), use_container_width=True)

else:
    st.error("Archivo CSV no encontrado.")
