import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="DIMAQUINAS C.A. - CONTROL DE OBRA", layout="wide", page_icon="🏗️")

# 2. DISEÑO CSS
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

# ─── Función para envolver texto en ejes (usando \n para Plotly) ───
def wrap_label(text, width=18):
    """Divide etiquetas largas en múltiples líneas para los ejes de Plotly."""
    if not isinstance(text, str):
        return str(text)
    words = text.split()
    lines, current = [], []
    for word in words:
        if sum(len(w) for w in current) + len(current) + len(word) > width:
            if current:
                lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "<br>".join(lines)

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
    except Exception as e:
        st.error(f"Error cargando CSV: {e}")
        return None

df = load_all_data()

if df is not None:
    # --- VARIABLES INICIALES ---
    empresa = df['EMPRESA'].iloc[0] if 'EMPRESA' in df.columns else "DIMAQUINAS C.A."
    obra    = df['OBRA'].iloc[0]    if 'OBRA'    in df.columns else "CALLE DOS OJOS"
    pct_admin = df['% ADMIN'].max() if '% ADMIN' in df.columns else 0

    df_gastos_base = df[df['CLASE'] == 'GASTO'].copy()
    df_ingresos    = df[df['CLASE'] == 'INGRESO'].copy()

    # --- BARRA LATERAL DE FILTROS ---
    st.sidebar.header("🎯 FILTROS DE OBRA")
    tipos_sel = st.sidebar.multiselect("Filtrar por TIPO:",      options=sorted(df_gastos_base['TIPO'].unique()))
    areas_sel = st.sidebar.multiselect("Filtrar por ÁREA:",      options=sorted(df_gastos_base['AREA'].unique()))
    prov_sel  = st.sidebar.multiselect("Filtrar por PROVEEDOR:", options=sorted(df_gastos_base['PROVEEDOR'].unique()))

    # Aplicar filtros
    df_gastos = df_gastos_base.copy()
    if tipos_sel: df_gastos = df_gastos[df_gastos['TIPO'].isin(tipos_sel)]
    if areas_sel: df_gastos = df_gastos[df_gastos['AREA'].isin(areas_sel)]
    if prov_sel:  df_gastos = df_gastos[df_gastos['PROVEEDOR'].isin(prov_sel)]

    # --- CÁLCULOS ---
    total_ing           = df_ingresos['MONTO BASE USD'].sum()
    total_neto          = df_gastos['MONTO BASE USD'].sum()
    total_honorarios    = df_gastos['HONORARIOS'].sum()
    # Gasto real total = neto + honorarios AD (fuente única de verdad para todo el dashboard)
    gasto_total_real    = total_neto + total_honorarios
    saldo_caja          = total_ing - gasto_total_real

    # --- ENCABEZADO ---
    st.markdown(
        f'<div class="header-box">'
        f'<p class="title-text">{empresa}</p>'
        f'<p class="subtitle-text">OBRA: {obra}</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    # --- MÉTRICAS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL INGRESOS",  f"$ {total_ing:,.2f}")
    m2.metric("NETO FILTRADO",   f"$ {total_neto:,.2f}")
    m3.metric("ADMIN. FILTRADA", f"$ {total_honorarios:,.2f}")
    m4.metric("SALDO CAJA",      f"$ {saldo_caja:,.2f}")

    st.divider()

    # ──────────────────────────────────────────────────────────
    # FUNCIÓN UNIFICADA PARA GRÁFICOS DE BARRAS HORIZONTALES
    # ──────────────────────────────────────────────────────────
    def horizontal_bar_chart(df_plot, x_col, y_col, color_scale, title, height=500):
        """
        Crea un gráfico de barras horizontales limpio con:
        - Etiquetas en formato $ dentro/fuera de la barra según espacio
        - Nombres de categorías que se ajustan automáticamente
        - Sin artefactos visuales de color_axis
        """
        if df_plot.empty:
            st.info("No hay datos para este gráfico con los filtros actuales.")
            return

        # Ordenar de mayor a menor para mejor legibilidad
        df_sorted = df_plot.sort_values(x_col, ascending=True).copy()

        # Etiquetas formateadas en USD
        labels = [f"$ {v:,.2f}" for v in df_sorted[x_col]]

        # Colores degradados (Plotly scale → lista de colores)
        n = len(df_sorted)
        # Normalizar valores para el color
        vals = df_sorted[x_col].values
        max_v = vals.max() if vals.max() > 0 else 1
        norm  = vals / max_v

        import plotly.colors as pc
        palette = pc.get_colorscale(color_scale)
        bar_colors = pc.sample_colorscale(palette, norm)

        fig = go.Figure(go.Bar(
            x           = df_sorted[x_col],
            y           = df_sorted[y_col],
            orientation = 'h',
            marker_color= bar_colors,
            text        = labels,
            textposition= 'outside',
            textfont    = dict(size=11, color='#1e3a8a', family='Arial Black'),
            cliponaxis  = False,
        ))

        # Calcular margen derecho según la longitud del texto más largo
        max_label_len = max(len(l) for l in labels)
        right_margin  = max(max_label_len * 7, 130)

        fig.update_layout(
            title       = dict(text=title, font=dict(size=14, color='#1e3a8a'), x=0.01),
            height      = height,
            margin      = dict(l=10, r=right_margin, t=50, b=30),
            xaxis       = dict(
                showticklabels = False,
                showgrid       = False,
                zeroline       = False,
                range          = [0, max_v * 1.35],
            ),
            yaxis       = dict(
                tickfont       = dict(size=11, color='#000000'),
                showgrid       = False,
            ),
            plot_bgcolor  = '#f8fafc',
            paper_bgcolor = '#ffffff',
            showlegend    = False,
        )

        st.plotly_chart(fig, use_container_width=True)

    # ──────────────────────────────────────────────────────────
    # TABS
    # ──────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs(["📊 GRÁFICOS", "💸 EGRESOS", "💰 INGRESOS", "🔍 BUSCADOR"])

    with t1:
        # ── 1. Por TIPO ──────────────────────────────────────
        st.write("### 📌 Inversión por Tipo")
        df_t = df_gastos.groupby('TIPO')['MONTO BASE USD'].sum().reset_index()
        df_t = pd.concat([df_t, pd.DataFrame({'TIPO': ['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        horizontal_bar_chart(df_t, 'MONTO BASE USD', 'TIPO', 'Viridis',
                             '📌 Inversión total por Tipo de Gasto', height=max(350, len(df_t) * 45))

        st.divider()

        # ── 2. Por ÁREA ──────────────────────────────────────
        st.write("### 📐 Inversión por Área")
        df_a = df_gastos.groupby('AREA')['MONTO BASE USD'].sum().reset_index()
        df_a = pd.concat([df_a, pd.DataFrame({'AREA': ['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        horizontal_bar_chart(df_a, 'MONTO BASE USD', 'AREA', 'Blues',
                             '📐 Inversión total por Área de Obra', height=max(400, len(df_a) * 42))

        st.divider()

        # ── 3. Top Proveedores ────────────────────────────────
        st.write("### 👥 Top Proveedores")
        df_p = (df_gastos.groupby('PROVEEDOR')['MONTO BASE USD']
                .sum().sort_values(ascending=False).head(20).reset_index())
        df_p = pd.concat([df_p, pd.DataFrame({'PROVEEDOR': ['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        horizontal_bar_chart(df_p, 'MONTO BASE USD', 'PROVEEDOR', 'Reds',
                             '👥 Top 20 Proveedores por Gasto', height=max(500, len(df_p) * 40))

        st.divider()

        # ── 4. Evolución acumulativa en el Tiempo ─────────────
        st.write("### 📅 Evolución Acumulativa de Gastos e Ingresos")

        # Selector semanas / meses
        freq_sel = st.radio(
            "Agrupación:",
            options=["📅 Mensual", "🗓️ Semanal"],
            horizontal=True,
            key="freq_time"
        )
        freq_code = "ME" if freq_sel == "📅 Mensual" else "W"

        # Rango: desde primer ingreso hasta hoy
        if not df_ingresos.empty:
            fecha_inicio = df_ingresos['FECHA'].min()
        else:
            fecha_inicio = df_gastos_base['FECHA'].min()
        fecha_hoy = pd.Timestamp.today().normalize()

        # Índice completo del período
        idx_full = pd.date_range(start=fecha_inicio, end=fecha_hoy, freq=freq_code)

        if not df_gastos.empty:
            # Siempre calculamos el gasto real como MONTO BASE USD + HONORARIOS
            # para que coincida exactamente con las métricas de arriba:
            #   NETO FILTRADO + ADMIN. FILTRADA = lo que veremos en el gráfico
            df_gastos_chart = df_gastos.copy()
            hon_col = df_gastos_chart['HONORARIOS'] if 'HONORARIOS' in df_gastos_chart.columns else 0
            df_gastos_chart['_GASTO_REAL'] = df_gastos_chart['MONTO BASE USD'] + hon_col

            s_gastos = (df_gastos_chart.set_index('FECHA')['_GASTO_REAL']
                        .resample(freq_code).sum()
                        .reindex(idx_full, fill_value=0)
                        .cumsum())


            # Ingresos por período → cumsum (siempre sobre datos completos, sin filtro)
            s_ingresos = (df_ingresos.set_index('FECHA')['MONTO BASE USD']
                          .resample(freq_code).sum()
                          .reindex(idx_full, fill_value=0)
                          .cumsum())

            df_evol = pd.DataFrame({
                'FECHA'   : idx_full,
                'GASTOS'  : s_gastos.values,
                'INGRESOS': s_ingresos.values,
            })

            fig_time = go.Figure()

            # Área de ingresos (fondo)
            fig_time.add_trace(go.Scatter(
                x=df_evol['FECHA'], y=df_evol['INGRESOS'],
                name='Ingresos Acum.',
                mode='lines',
                line=dict(color='#22c55e', width=2),
                fill='tozeroy',
                fillcolor='rgba(34,197,94,0.15)',
                hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Ingresos: $ %{y:,.2f}<extra></extra>',
            ))

            # Área de gastos (encima) — incluye Honorarios de Administración Delegada
            fig_time.add_trace(go.Scatter(
                x=df_evol['FECHA'], y=df_evol['GASTOS'],
                name='Gastos + Admin. Acum.',
                mode='lines+markers',
                line=dict(color='#1e3a8a', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(30,58,138,0.18)',
                marker=dict(size=5, color='#1e3a8a'),
                hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Gastos: $ %{y:,.2f}<extra></extra>',
            ))

            # Línea vertical "hoy" — usando add_shape + add_annotation por compatibilidad con Plotly en Python 3.14
            hoy_str = fecha_hoy.strftime('%Y-%m-%d')
            fig_time.add_shape(
                type='line',
                x0=hoy_str, x1=hoy_str,
                y0=0, y1=1,
                xref='x', yref='paper',
                line=dict(color='#ef4444', width=1.5, dash='dot'),
            )
            fig_time.add_annotation(
                x=hoy_str, y=1,
                xref='x', yref='paper',
                text='HOY', showarrow=False,
                xanchor='left', yanchor='top',
                font=dict(color='#ef4444', size=11, family='Arial Black'),
            )

            lbl = "Mes" if freq_sel == "📅 Mensual" else "Semana"
            fig_time.update_layout(
                height=420,
                plot_bgcolor='#f8fafc',
                paper_bgcolor='#ffffff',
                margin=dict(l=10, r=20, t=40, b=30),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                xaxis=dict(
                    title=lbl,
                    range=[fecha_inicio, fecha_hoy],
                    showgrid=True, gridcolor='#e5e7eb',
                    tickformat='%b %Y' if freq_sel == "📅 Mensual" else '%d %b %Y',
                ),
                yaxis=dict(
                    title='USD acumulado',
                    tickprefix='$ ', tickformat=',.0f',
                    showgrid=True, gridcolor='#e5e7eb',
                ),
                hovermode='x unified',
            )

            st.plotly_chart(fig_time, use_container_width=True)

            # Mini resumen debajo del gráfico
            # Usamos las mismas variables de las métricas de arriba → siempre coinciden
            color_sal = "🟢" if saldo_caja >= 0 else "🔴"
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos Acumulados",       f"$ {total_ing:,.2f}")
            c2.metric("Gastos + Admin. Acumulados", f"$ {gasto_total_real:,.2f}")
            c3.metric(f"{color_sal} Saldo Neto",    f"$ {saldo_caja:,.2f}")

    with t2:
        st.subheader("📝 Detalle de Gastos")
        cols_show = [c for c in ['FECHA', 'TIPO', 'AREA', 'PROVEEDOR', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL'] if c in df_gastos.columns]
        fmt = {c: "${:,.2f}" for c in ['MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL'] if c in cols_show}
        st.dataframe(
            df_gastos[cols_show].sort_values('FECHA', ascending=False).style.format(fmt),
            use_container_width=True
        )

    with t3:
        st.subheader("💰 Detalle de Ingresos")
        cols_ing = [c for c in ['FECHA', 'PROVEEDOR', 'MONTO BASE USD'] if c in df_ingresos.columns]
        st.dataframe(
            df_ingresos[cols_ing].sort_values('FECHA', ascending=False).style.format({"MONTO BASE USD": "${:,.2f}"}),
            use_container_width=True
        )

    with t4:
        st.subheader("🔍 Buscador")
        q = st.text_input("Escriba una palabra para buscar en todos los campos:")
        if q:
            mask = df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)
            res  = df[mask]
            st.success(f"Registros encontrados: {len(res)} | Total: $ {res['MONTO BASE USD'].sum():,.2f}")
            fmt_res = {c: "${:,.2f}" for c in ['MONTO BASE USD', 'COSTO TOTAL', 'HONORARIOS'] if c in res.columns}
            fmt_res.update({c: "{:,.2f}" for c in ['MONTO ORIG', 'TASA'] if c in res.columns})
            st.dataframe(res.style.format(fmt_res), use_container_width=True)

else:
    st.error("❌ No se encontró el archivo CSV 'DIMAQUINAS CALLE DOS OJOS.csv'. Verifica que esté en el mismo directorio.")
