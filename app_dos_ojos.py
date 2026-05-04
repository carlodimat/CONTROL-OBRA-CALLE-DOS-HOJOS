import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Configuración premium
st.set_page_config(page_title="CONTROL PRO: CALLE DOS OJOS", layout="wide", page_icon="💰")

# Estilos CSS para que se vea impecable
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { border: 1px solid #d1d5db; padding: 20px; border-radius: 12px; background: white; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    .main-title { color: #1e3a8a; font-size: 40px; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def get_data():
    try:
        df = pd.read_csv("DIMAQUINAS CALLE DOS OJOS.csv")
        df['FECHA'] = pd.to_datetime(df['FECHA'])
        for col in ['MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return None

df = get_data()

if df is not None:
    # --- SIDEBAR ---
    st.sidebar.title("📊 CONFIGURACIÓN")
    area = st.sidebar.number_input("Área Obra (m²)", value=850.0)
    admin_pct = st.sidebar.slider("% Admin Delegada", 0, 20, 10) / 100
    
    # --- CÁLCULOS ---
    df_gastos = df[df['CLASE'] == 'GASTO'].copy()
    df_ingresos = df[df['CLASE'] == 'INGRESO'].copy()
    
    total_ing = df_ingresos['MONTO BASE USD'].sum()
    total_gas_neto = df_gastos['MONTO BASE USD'].sum()
    total_admin = total_gas_neto * admin_pct
    total_obra = total_gas_neto + total_admin
    total_pagado = df_gastos['MONTO PAGADO'].sum() * (1 + admin_pct)
    saldo_caja = total_ing - total_pagado

    # --- ENCABEZADO ---
    st.markdown('<p class="main-title">🏗️ CONTROL ADMINISTRATIVO: CALLE DOS OJOS</p>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("TOTAL INGRESOS", f"$ {total_ing:,.2f}")
    col2.metric("COSTO TOTAL OBRA", f"$ {total_obra:,.2f}", f"Admin: ${total_admin:,.0f}")
    col3.metric("PAGADO A LA FECHA", f"$ {total_pagado:,.2f}")
    col4.metric("SALDO DISPONIBLE", f"$ {saldo_caja:,.2f}", delta_color="normal")

    st.divider()

    # --- PESTAÑAS ---
    t1, t2, t3, t4 = st.tabs(["📈 GRÁFICOS Y ANÁLISIS", "💸 LISTA DE EGRESOS", "💰 LISTA DE INGRESOS", "🔍 BUSCADOR INTELIGENTE"])

    with t1:
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.write("### 🏆 Top Proveedores (Egresos)")
            prov_data = df_gastos.groupby('PROVEEDOR')['MONTO BASE USD'].sum().sort_values(ascending=False).head(10).reset_index()
            if not prov_data.empty:
                fig_prov = px.bar(prov_data, x='MONTO BASE USD', y='PROVEEDOR', orientation='h',
                                  color='MONTO BASE USD', color_continuous_scale='Viridis',
                                  text_auto=',.2f', title="Top 10 Proveedores por Monto ($)")
                fig_prov.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_prov, use_container_width=True)
            else:
                st.info("No hay datos de proveedores para mostrar.")
            
        with c_right:
            st.write("### 🏗️ Inversión por Disciplina")
            area_data = df_gastos.groupby('AREA')['MONTO BASE USD'].sum().reset_index()
            if not area_data.empty:
                fig_area = px.pie(area_data, values='MONTO BASE USD', names='AREA', hole=0.4,
                                  color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_area, use_container_width=True)
            else:
                st.info("No hay datos por área para mostrar.")

    with t2:
        st.subheader("📝 Detalle Completo de Egresos (Gastos)")
        st.write(f"Suma Neta de Egresos: **$ {total_gas_neto:,.2f}**")
        df_egresos_disp = df_gastos[['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'AREA', 'MONTO BASE USD', 'ESTADO']].sort_values('FECHA', ascending=False)
        st.dataframe(df_egresos_disp.style.format({"MONTO BASE USD": "${:,.2f}"}), use_container_width=True)

    with t3:
        st.subheader("📥 Detalle de Ingresos (Abonos)")
        st.write(f"Suma de Ingresos: **$ {total_ing:,.2f}**")
        df_ing_disp = df_ingresos[['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONTO BASE USD']].sort_values('FECHA', ascending=False)
        st.dataframe(df_ing_disp.style.format({"MONTO BASE USD": "${:,.2f}"}), use_container_width=True)

    with t4:
        st.subheader("🔍 Buscador Multivariable")
        search_query = st.text_input("Escribe el nombre del proveedor, material o disciplina:")
        
        if search_query:
            mask = df.apply(lambda r: r.astype(str).str.contains(search_query, case=False, regex=False).any(), axis=1)
            df_search = df[mask]
            
            if not df_search.empty:
                st.success(f"Encontrados {len(df_search)} registros para '{search_query}'")
                
                s_ing = df_search[df_search['CLASE'] == 'INGRESO']['MONTO BASE USD'].sum()
                s_gas = df_search[df_search['CLASE'] == 'GASTO']['MONTO BASE USD'].sum()
                
                s1, s2 = st.columns(2)
                s1.info(f"Ingresos en búsqueda: $ {s_ing:,.2f}")
                s2.warning(f"Gastos en búsqueda: $ {s_gas:,.2f}")
                
                st.dataframe(df_search.style.format({"MONTO BASE USD": "${:,.2f}", "MONTO PAGADO": "${:,.2f}"}), use_container_width=True)
            else:
                st.error("No se encontraron resultados.")
else:
    st.error("⚠️ Error: No se pudo cargar el archivo 'DIMAQUINAS CALLE DOS OJOS.csv'. Verifica que el nombre sea exacto.")
