import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import io

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

def create_pdf(df_report, title_report, totals_info=""):
    """Genera un buffer de PDF a partir de un DataFrame."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    # Encabezado
    pdf.cell(190, 10, title_report, ln=True, align='C')
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Generado el: {pd.Timestamp.today().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    
    if totals_info:
        pdf.set_font("Arial", "B", 10)
        pdf.multi_cell(190, 10, totals_info)
        pdf.ln(5)

    # Tabla
    pdf.set_font("Arial", "B", 8)
    # Seleccionar columnas mas importantes para que quepan en el ancho
    cols = [c for c in ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONTO ORIG', 'HONORARIOS', 'COSTO TOTAL'] if c in df_report.columns]
    
    # Anchos de columna proporcionales
    widths = [20, 35, 65, 25, 20, 25]
    
    # Cabecera de tabla
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 8, col, border=1, align='C')
    pdf.ln()
    
    # Datos
    pdf.set_font("Arial", "", 7)
    for _, row in df_report.iterrows():
        for i, col in enumerate(cols):
            val = str(row[col])
            if 'MONTO' in col or 'HONORARIOS' in col or 'COSTO' in col:
                try: val = f"{float(row[col]):,.2f}"
                except: pass
            elif 'FECHA' in col:
                try: val = row[col].strftime('%d/%m/%Y')
                except: pass
            
            # Truncar descripcion si es muy larga
            if col == 'DESCRIPCION' and len(val) > 45: val = val[:42] + "..."
                
            pdf.cell(widths[i], 7, val, border=1)
        pdf.ln()
        
    return pdf.output()

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
    total_ing        = df_ingresos['MONTO BASE USD'].sum()
    total_neto       = df_gastos['MONTO BASE USD'].sum()          # filtrado (para filter_summary)
    total_honorarios = df_gastos['HONORARIOS'].sum()              # filtrado (para filter_summary)
    gasto_total_real = total_neto + total_honorarios              # filtrado (para filter_summary)
    saldo_caja       = total_ing - gasto_total_real               # filtrado (para filter_summary)

    # Totales REALES sin filtrar — se usan en las métricas fijas de arriba y el resumen del gráfico
    _hon_base       = df_gastos_base['HONORARIOS'].sum() if 'HONORARIOS' in df_gastos_base.columns else 0
    neto_base       = df_gastos_base['MONTO BASE USD'].sum()
    gasto_base_real = neto_base + _hon_base
    saldo_base_real = total_ing - gasto_base_real

    # --- ENCABEZADO ---
    st.markdown(
        f'<div class="header-box">'
        f'<p class="title-text">{empresa}</p>'
        f'<p class="subtitle-text">OBRA: {obra}</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    # --- MÉTRICAS (siempre valores reales del proyecto, sin filtrar) ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL INGRESOS",   f"$ {total_ing:,.2f}")
    m2.metric("GASTOS NETOS",     f"$ {neto_base:,.2f}")
    m3.metric("ADMIN. DELEGADA",  f"$ {_hon_base:,.2f}")
    m4.metric("SALDO REAL",       f"$ {saldo_base_real:,.2f}")

    st.divider()

    # ──────────────────────────────────────────────────────────
    # FUNCIÓN UNIFICADA PARA GRÁFICOS DE BARRAS HORIZONTALES
    # ──────────────────────────────────────────────────────────
    def horizontal_bar_chart(df_plot, x_col, y_col, color_scale, title, height=500, count_col=None):
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

        # Etiquetas formateadas en USD incluyendo conteo si existe
        if count_col and count_col in df_sorted.columns:
            labels = []
            for v, c in zip(df_sorted[x_col], df_sorted[count_col]):
                if c == "N/A":
                    labels.append(f"$ {v:,.2f}")
                else:
                    labels.append(f"$ {v:,.2f} ({int(c)} reg)")
        else:
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

    # Helper: muestra resumen de filtro debajo de cada gráfico
    filtro_activo = bool(tipos_sel or areas_sel or prov_sel)
    def filter_summary(df_filtrado, label_filtro):
        if filtro_activo:
            n   = len(df_filtrado)
            tot = df_filtrado['MONTO BASE USD'].sum()
            st.markdown(
                f"""<div style='background:#e8f0fe;border-left:5px solid #1e3a8a;
                padding:10px 16px;border-radius:6px;margin-top:4px;font-size:1rem;'>
                🔍 <b>Filtro activo — {label_filtro}:</b> &nbsp;
                {n} registro{'s' if n != 1 else ''} &nbsp;|
                Subtotal neto: <b>$ {tot:,.2f}</b> &nbsp;|
                + Admin. Delegada: <b>$ {total_honorarios:,.2f}</b> &nbsp;|
                Total real: <b>$ {tot + total_honorarios:,.2f}</b>
                </div>""",
                unsafe_allow_html=True
            )

    with t1:
        # ── 1. Por TIPO ──────────────────────────────────────
        st.write("### 📌 Inversión por Tipo")
        st.info(f"📊 **{len(df_gastos)}** registros de gastos filtrados - Subtotal: **$ {total_neto:,.2f}**")
        df_t = df_gastos.groupby('TIPO')['MONTO BASE USD'].sum().reset_index()
        df_t = pd.concat([df_t, pd.DataFrame({'TIPO': ['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        horizontal_bar_chart(df_t, 'MONTO BASE USD', 'TIPO', 'Viridis',
                             '📌 Inversión total por Tipo de Gasto', height=max(350, len(df_t) * 45))
        filter_summary(df_gastos, "Tipo" + (f": {', '.join(tipos_sel)}" if tipos_sel else ""))

        st.divider()

        # ── 2. Por ÁREA ──────────────────────────────────────
        st.write("### 📐 Inversión por Área")
        df_a = df_gastos.groupby('AREA')['MONTO BASE USD'].sum().reset_index()
        df_a = pd.concat([df_a, pd.DataFrame({'AREA': ['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        horizontal_bar_chart(df_a, 'MONTO BASE USD', 'AREA', 'Blues',
                             '📐 Inversión total por Área de Obra', height=max(400, len(df_a) * 42))
        filter_summary(df_gastos, "Área" + (f": {', '.join(areas_sel)}" if areas_sel else ""))

        st.divider()

        # ── 3. Top Proveedores ────────────────────────────────
        st.write("### 👥 Top Proveedores")
        df_p = (df_gastos.groupby('PROVEEDOR')['MONTO BASE USD']
                .sum().sort_values(ascending=False).head(20).reset_index())
        df_p = pd.concat([df_p, pd.DataFrame({'PROVEEDOR': ['ADMINISTRACIÓN DELEGADA'], 'MONTO BASE USD': [total_honorarios]})], ignore_index=True)
        horizontal_bar_chart(df_p, 'MONTO BASE USD', 'PROVEEDOR', 'Reds',
                             '👥 Top 20 Proveedores por Gasto', height=max(500, len(df_p) * 40))
        filter_summary(df_gastos, "Proveedor" + (f": {', '.join(prov_sel)}" if prov_sel else ""))

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

            # Mini resumen debajo del gráfico — 4 columnas, siempre sin filtrar
            color_sal_base = "🟢" if saldo_base_real >= 0 else "🔴"
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Ingresos Totales",   f"$ {total_ing:,.2f}")
            b2.metric("Gastos Netos",       f"$ {neto_base:,.2f}")
            b3.metric("Admin. Delegada",    f"$ {_hon_base:,.2f}")
            b4.metric(f"{color_sal_base} Saldo Real", f"$ {saldo_base_real:,.2f}")
            if filtro_activo:
                st.caption("⚠️ Valores del proyecto completo (sin filtros). "
                           "El detalle filtrado se muestra debajo de cada gráfico.")

    with t2:
        st.subheader("📝 Detalle de Gastos")
        st.info(f"📋 **{len(df_gastos)}** movimientos de gastos en esta vista - Total Neto: **$ {total_neto:,.2f}**")
        
        # Columnas estandarizadas
        cols_show = [c for c in ['FECHA', 'TIPO', 'AREA', 'PROVEEDOR', 'DESCRIPCION', 'MONTO ORIG', '% ADMIN', 'HONORARIOS', 'COSTO TOTAL'] if c in df_gastos.columns]
        
        fmt = {c: "${:,.2f}" for c in ['HONORARIOS', 'COSTO TOTAL', 'MONTO BASE USD'] if c in cols_show}
        fmt.update({c: "{:,.2f}" for c in ['MONTO ORIG', '% ADMIN'] if c in cols_show})
        
        st.dataframe(
            df_gastos[cols_show].sort_values('FECHA', ascending=False).style.format(fmt),
            use_container_width=True
        )

        # Boton de PDF para Egresos
        summary_text = f"Total Neto: $ {total_neto:,.2f} | Admin: $ {total_honorarios:,.2f} | Total Real: $ {gasto_total_real:,.2f}"
        pdf_data = create_pdf(df_gastos.sort_values('FECHA', ascending=False), f"REPORTE DE EGRESOS - {obra}", summary_text)
        st.download_button(
            label="📄 Descargar Egresos en PDF",
            data=pdf_data,
            file_name=f"Egresos_{obra}_{pd.Timestamp.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )


    with t3:
        st.subheader("💰 Detalle de Ingresos")
        st.success(f"💵 **{len(df_ingresos)}** ingresos registrados - Total: **$ {total_ing:,.2f}**")
        cols_ing = [c for c in ['FECHA', 'PROVEEDOR', 'MONTO BASE USD'] if c in df_ingresos.columns]
        st.dataframe(
            df_ingresos[cols_ing].sort_values('FECHA', ascending=False).style.format({"MONTO BASE USD": "${:,.2f}"}),
            use_container_width=True
        )

        # Boton de PDF para Ingresos
        summary_ing = f"Total Ingresos: $ {total_ing:,.2f}"
        pdf_ing = create_pdf(df_ingresos.sort_values('FECHA', ascending=False), f"REPORTE DE INGRESOS - {obra}", summary_ing)
        st.download_button(
            label="📄 Descargar Ingresos en PDF",
            data=pdf_ing,
            file_name=f"Ingresos_{obra}_{pd.Timestamp.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )


    with t4:
        st.subheader("🔍 Buscador por Descripción")
        q = st.text_input("📝 Escriba una palabra exacta para buscar en la columna DESCRIPCIÓN:")
        if q:
            import re
            if 'DESCRIPCION' not in df.columns:
                st.warning("⚠️ La columna DESCRIPCION no existe en el CSV.")
            else:
                # Quitamos \b para que sea mas flexible (ej: Cabilla encuentra Cabillas)
                pattern = re.escape(q) 
                mask = df['DESCRIPCION'].astype(str).str.contains(pattern, case=False, regex=True)
                res  = df[mask]
                
                # Calculamos los totales de la busqueda
                s_orig = res['MONTO ORIG'].sum() if 'MONTO ORIG' in res.columns else 0
                s_hon  = res['HONORARIOS'].sum() if 'HONORARIOS' in res.columns else 0
                s_total = res['COSTO TOTAL'].sum() if 'COSTO TOTAL' in res.columns else 0

                st.success(
                    f"🔍 **{len(res)}** registros encontrados con **‘{q}’** en DESCRIPCIÓN\n\n"
                    f"💰 **Totales:** Neto Orig: **{s_orig:,.2f}** | Admin: **$ {s_hon:,.2f}** | Total: **$ {s_total:,.2f}**"
                )
                
                # Seleccionamos las columnas solicitadas
                cols_buscador = [c for c in ['FECHA', 'TIPO', 'AREA', 'PROVEEDOR', 'DESCRIPCION', 'MONTO ORIG', '% ADMIN', 'HONORARIOS', 'COSTO TOTAL'] if c in res.columns]
                
                fmt_res = {c: "${:,.2f}" for c in ['HONORARIOS', 'COSTO TOTAL', 'MONTO BASE USD'] if c in res.columns}
                fmt_res.update({c: "{:,.2f}" for c in ['MONTO ORIG', '% ADMIN'] if c in res.columns})
                
                st.dataframe(
                    res[cols_buscador].sort_values('FECHA', ascending=False).style.format(fmt_res), 
                    use_container_width=True
                )

else:
    st.error("❌ No se encontró el archivo CSV 'DIMAQUINAS CALLE DOS OJOS.csv'. Verifica que esté en el mismo directorio.")
