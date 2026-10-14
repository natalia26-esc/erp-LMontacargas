import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import io
import math
from supabase import create_client, Client

# Configuración de la página
st.set_page_config(page_title="ERP Montacargas - Control Financiero", layout="wide")

# ==========================================
# CONEXIÓN A SUPABASE
# ==========================================
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Error de conexión a Supabase: Verifica tus Secrets. Detalles: {e}")
    st.stop()

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def get_catalogo(tabla):
    res = supabase.table(tabla).select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def get_equipos_catalogo_df():
    return get_catalogo("cat_equipos")

def get_equipos_catalogo_tuples():
    res = supabase.table("cat_equipos").select("id, eco, marca, modelo, serie, cliente").execute()
    if res.data:
        return [(d['id'], d['eco'], d['marca'], d['modelo'], d['serie'], d['cliente']) for d in res.data]
    return []

def generar_id(tipo_prefijo, fecha_str):
    try:
        dt_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
        fecha_formateada = dt_obj.strftime("%d%m%Y")
        tabla = "trabajos" if tipo_prefijo == "tr" else ("gastos" if tipo_prefijo == "ga" else "rentas")
        
        prefix = f"{tipo_prefijo}_{fecha_formateada}_"
        
        res = supabase.table(tabla).select("id_personalizado").execute()
        
        if res.data:
            ids_del_dia = [r['id_personalizado'] for r in res.data if r['id_personalizado'] and str(r['id_personalizado']).startswith(prefix)]
            if not ids_del_dia:
                return f"{prefix}001"
                
            max_num = 0
            for id_val in ids_del_dia:
                try:
                    num = int(str(id_val).split("_")[-1])
                    if num > max_num:
                        max_num = num
                except:
                    pass
            return f"{prefix}{max_num + 1:03d}"
        else:
            return f"{prefix}001"
            
    except Exception as e:
        return f"{tipo_prefijo}_error_000"

def get_capital_inicial():
    res = supabase.table("config").select("valor").eq("clave", "capital_inicial").execute()
    if res.data:
        return float(res.data[0]['valor'])
    return 0.0

def set_capital_inicial(monto):
    supabase.table("config").upsert({"clave": "capital_inicial", "valor": float(monto)}).execute()

def clean_records_for_supabase(df):
    """Fuerza bruta para limpiar el DataFrame de cualquier NaN, error de JSON y espacios vacíos"""
    raw_records = df.to_dict(orient='records')
    
    clean_records = []
    for row in raw_records:
        clean_row = {}
        for key, val in row.items():
            if pd.isna(val):
                clean_row[key] = None
            elif isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                clean_row[key] = None
            elif hasattr(val, 'strftime'):
                clean_row[key] = val.strftime('%Y-%m-%d')
            elif isinstance(val, str):
                val_limpio = val.strip()
                clean_row[key] = val_limpio if val_limpio != "" else None
            else:
                clean_row[key] = val
        clean_records.append(clean_row)
        
    return clean_records

# ==========================================
# ENCABEZADO
# ==========================================
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
    elif os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=120)
    else:
        st.write("📌 [Sube logo.png]")

with col_title:
    st.title("🚜 ERP Ángel & Montalvo - Control de Montacargas")

# ==========================================
# BARRA LATERAL (Respaldo en la nube)
# ==========================================
with st.sidebar:
    st.header("🛡️ Respaldo del Sistema")
    st.write("Descarga todo tu ERP en Excel:")
    
    df_t_ex = pd.DataFrame(supabase.table("trabajos").select("*").execute().data)
    df_g_ex = pd.DataFrame(supabase.table("gastos").select("*").execute().data)
    df_r_ex = pd.DataFrame(supabase.table("rentas").select("*").execute().data)
    df_cli_ex = pd.DataFrame(supabase.table("cat_clientes").select("*").execute().data)
    df_eq_ex = pd.DataFrame(supabase.table("cat_equipos").select("*").execute().data)
    df_cat_ex = pd.DataFrame(supabase.table("cat_categorias").select("*").execute().data)
    df_sub_ex = pd.DataFrame(supabase.table("cat_subcategorias").select("*").execute().data)
    df_prov_ex = pd.DataFrame(supabase.table("cat_proveedores").select("*").execute().data)
    df_cta_ex = pd.DataFrame(supabase.table("cat_cuentas").select("*").execute().data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if not df_t_ex.empty: df_t_ex.to_excel(writer, sheet_name='Trabajos', index=False)
        if not df_g_ex.empty: df_g_ex.to_excel(writer, sheet_name='Gastos', index=False)
        if not df_r_ex.empty: df_r_ex.to_excel(writer, sheet_name='Rentas', index=False)
        if not df_cli_ex.empty: df_cli_ex.to_excel(writer, sheet_name='Clientes', index=False)
        if not df_eq_ex.empty: df_eq_ex.to_excel(writer, sheet_name='Equipos', index=False)
        if not df_cat_ex.empty: df_cat_ex.to_excel(writer, sheet_name='Categorias', index=False)
        if not df_sub_ex.empty: df_sub_ex.to_excel(writer, sheet_name='Subcategorias', index=False)
        if not df_prov_ex.empty: df_prov_ex.to_excel(writer, sheet_name='Proveedores', index=False)
        if not df_cta_ex.empty: df_cta_ex.to_excel(writer, sheet_name='Cuentas', index=False)
    
    excel_data = output.getvalue()
    st.download_button(
        label="📥 Descargar Respaldo (.xlsx)",
        data=excel_data,
        file_name=f"Respaldo_Nube_ERP_{datetime.today().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    st.header("📤 Restaurar / Importar Excel")
    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=['xlsx'])
    
    if uploaded_file is not None:
        if st.button("🚨 Cargar y Sobrescribir en Nube"):
            xls = pd.ExcelFile(uploaded_file)
            tablas_map = {
                'Trabajos': 'trabajos', 'Gastos': 'gastos', 'Rentas': 'rentas',
                'Clientes': 'cat_clientes', 'Equipos': 'cat_equipos',
                'Categorias': 'cat_categorias', 'Subcategorias': 'cat_subcategorias',
                'Proveedores': 'cat_proveedores', 'Cuentas': 'cat_cuentas'
            }
            try:
                for sheet, table_name in tablas_map.items():
                    if sheet in xls.sheet_names:
                        df_sheet = pd.read_excel(xls, sheet_name=sheet)
                        
                        if 'id_personalizado' in df_sheet.columns:
                            df_sheet = df_sheet.dropna(subset=['id_personalizado'])
                            df_sheet = df_sheet.drop_duplicates(subset=['id_personalizado'], keep='last')
                        elif 'id' in df_sheet.columns:
                            df_sheet = df_sheet.dropna(subset=['id'])
                            df_sheet = df_sheet.drop_duplicates(subset=['id'], keep='last')
                        else:
                            df_sheet = df_sheet.dropna(how='all')
                            df_sheet = df_sheet.drop_duplicates()
                        
                        records = clean_records_for_supabase(df_sheet)
                        
                        if records:
                            supabase.table(table_name).upsert(records).execute()
                st.success("¡Base de datos restaurada con éxito en Supabase!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al importar: {e}")

# ==========================================
# PESTAÑAS PRINCIPALES
# ==========================================
tab_dash, tab_trabajos, tab_gastos, tab_rentas, tab_config = st.tabs([
    "📊 Dashboard e Indicadores", 
    "💼 Trabajos y Operaciones", 
    "💸 Gastos y Trazabilidad", 
    "🛞 Módulo de Rentas",
    "⚙️ Configuración y Catálogos"
])

# ==========================================
# PESTAÑA 1: DASHBOARD
# ==========================================
with tab_dash:
    st.header("Panel Directivo de Indicadores")
    
    df_t = pd.DataFrame(supabase.table("trabajos").select("*").execute().data)
    df_g = pd.DataFrame(supabase.table("gastos").select("*").execute().data)
    
    col_m1, col_m2 = st.columns(2)
    anos_disponibles = [str(datetime.now().year)]
    if not df_t.empty:
        df_t['fecha_dt'] = pd.to_datetime(df_t['fecha'], errors='coerce')
        anos_t = df_t['fecha_dt'].dt.year.dropna().unique()
        anos_disponibles = sorted(list(set([str(int(y)) for y in anos_t] + [str(datetime.now().year)])))
        
    anio_sel = col_m1.selectbox("Seleccionar Año", anos_disponibles, index=len(anos_disponibles)-1)
    
    meses_nombres = ["Todos", "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio", 
                     "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"]
    mes_actual_num = datetime.now().month
    mes_sel = col_m2.selectbox("Seleccionar Mes", meses_nombres, index=mes_actual_num)
    
    df_t_f = pd.DataFrame()
    df_g_f = pd.DataFrame()
    
    if not df_t.empty:
        df_t_f = df_t.copy()
        df_t_f['dt'] = pd.to_datetime(df_t_f['fecha'], errors='coerce')
        df_t_f = df_t_f[df_t_f['dt'].dt.year == int(anio_sel)]
        if mes_sel != "Todos":
            num_mes = int(mes_sel.split(" - ")[0])
            df_t_f = df_t_f[df_t_f['dt'].dt.month == num_mes]
            
    if not df_g.empty:
        df_g_f = df_g.copy()
        df_g_f['dt'] = pd.to_datetime(df_g_f['fecha'], errors='coerce')
        df_g_f = df_g_f[df_g_f['dt'].dt.year == int(anio_sel)]
        if mes_sel != "Todos":
            num_mes = int(mes_sel.split(" - ")[0])
            df_g_f = df_g_f[df_g_f['dt'].dt.month == num_mes]

    num_trabajos_mes = len(df_t_f)
    
    cotizado_mes = 0.0
    facturado_mes = 0.0
    num_facturas = 0
    cobrado_mes = 0.0
    pendiente_mes = 0.0
    costo_fiscal_mes = 0.0
    subtotal_ingresos_reales = 0.0
    iva_total_mes = 0.0
    
    if not df_t_f.empty:
        df_cotizados_mes = df_t_f[df_t_f['estado_financiero'].isin(['Por Cotizar', 'Cotizado']) | (df_t_f['estado_trabajo'] == 'N/A (Cotización)')]
        cotizado_mes = df_cotizados_mes['subtotal'].astype(float).sum() if not df_cotizados_mes.empty else 0.0

        df_facturados_mes = df_t_f[df_t_f['estado_financiero'].isin(['Facturado', 'Pagado']) | (df_t_f['factura'].notna() & (df_t_f['factura'] != ''))]
        facturado_mes = df_facturados_mes['total'].astype(float).sum() if not df_facturados_mes.empty else 0.0
        num_facturas = df_facturados_mes.shape[0]
        
        df_pagados_mes = df_t_f[df_t_f['estado_pago'] == 'Pagado']
        cobrado_mes = df_pagados_mes['total'].astype(float).sum() if not df_pagados_mes.empty else 0.0
        
        df_pendientes_cobro = df_t_f[(df_t_f['estado_pago'] != 'Pagado') & (df_t_f['estado_financiero'].isin(['Aprobado', 'Facturado']))]
        pendiente_mes = df_pendientes_cobro['total'].astype(float).sum() if not df_pendientes_cobro.empty else 0.0
        
        for _, row in df_pagados_mes.iterrows():
            sub_val = float(row.get('subtotal', 0.0)) if pd.notna(row.get('subtotal')) else 0.0
            iva_val = float(row.get('iva', 0.0)) if pd.notna(row.get('iva')) else 0.0
            subtotal_ingresos_reales += sub_val
            iva_total_mes += iva_val
            if str(row.get('cuenta_deposito')).strip() == 'Cansino':
                costo_fiscal_mes += sub_val * 0.08
                
    iva_gastos_mes = df_g_f['iva'].astype(float).sum() if not df_g_f.empty else 0.0
    gastos_totales_mes = df_g_f['total'].astype(float).sum() if not df_g_f.empty else 0.0
    
    # NUEVO CÁLCULO UNIFICADO DE UTILIDAD NETA REAL
    utilidad_neta_real = subtotal_ingresos_reales - costo_fiscal_mes - gastos_totales_mes
    comp_3_mes = utilidad_neta_real * 0.03 if utilidad_neta_real > 0 else 0.0
    
    fac_angel = 0.0
    fac_montalvo = 0.0
    if not df_t_f.empty:
        df_socios = df_t_f[df_t_f['estado_financiero'].isin(['Facturado', 'Pagado'])]
        if not df_socios.empty:
            fac_angel = df_socios[df_socios['facturado_por'] == 'Angel Llanez']['total'].astype(float).sum()
            fac_montalvo = df_socios[df_socios['facturado_por'] == 'Adolfo Montalvo']['total'].astype(float).sum()
    
    df_pagados_mes_actual = df_t_f[df_t_f['estado_pago'] == 'Pagado'] if not df_t_f.empty else pd.DataFrame()
    ing_angel_cuenta = df_pagados_mes_actual[df_pagados_mes_actual['cuenta_deposito'] == 'Cuenta Llanez']['total'].astype(float).sum() if not df_pagados_mes_actual.empty else 0.0
    ing_montalvo_cuenta = df_pagados_mes_actual[df_pagados_mes_actual['cuenta_deposito'] == 'Cuenta Montalvo']['total'].astype(float).sum() if not df_pagados_mes_actual.empty else 0.0
    ing_cansino = df_pagados_mes_actual[df_pagados_mes_actual['cuenta_deposito'] == 'Cansino']['total'].astype(float).sum() if not df_pagados_mes_actual.empty else 0.0
    
    df_todos_pagados_hist = df_t[df_t['estado_pago'] == 'Pagado'] if not df_t.empty else pd.DataFrame()
    subtotal_hist_pagados = df_todos_pagados_hist['subtotal'].astype(float).sum() if not df_todos_pagados_hist.empty else 0.0
    total_hist_gastos = df_g['total'].astype(float).sum() if not df_g.empty else 0.0
    
    capital_inicial = get_capital_inicial()
    capital_total_actual = capital_inicial + subtotal_hist_pagados - total_hist_gastos
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Cotizado (Total)", f"${cotizado_mes:,.2f}")
    c2.metric("Facturado", f"${facturado_mes:,.2f}", f"{num_facturas} Facturas")
    c3.metric("Pagado (Cobrado)", f"${cobrado_mes:,.2f}")
    c4.metric("Pendiente de Cobro", f"${pendiente_mes:,.2f}")
    c5.metric("Costo Fiscal", f"${costo_fiscal_mes:,.2f}")
    c6.metric("IVA del Mes (Cobrado)", f"${iva_total_mes:,.2f}", f"IVA Gastos: ${iva_gastos_mes:,.2f}")
    
    c7, c8, c9, c10, c11 = st.columns(5)
    c7.metric("Capital Total Actual", f"${capital_total_actual:,.2f}", "sin IVA y sin gastos")
    c8.metric("Gastos del Mes", f"${gastos_totales_mes:,.2f}")
    c9.metric("Utilidad Neta Real", f"${utilidad_neta_real:,.2f}", "Subtotal - Costo - Gastos")
    c10.metric("Compensación 3%", f"${comp_3_mes:,.2f}")
    c11.metric("Trabajos del Mes", f"{num_trabajos_mes}")
    
    st.markdown("---")
    
    st.subheader(f"👥 Control y Rendimiento por Socio (Filtrado por: {mes_sel})")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Facturado por Ángel Llanez (AL)", f"${fac_angel:,.2f}")
    sc2.metric("Facturado por Adolfo Montalvo (AM)", f"${fac_montalvo:,.2f}")
    sc3.metric("Ingresos en Cuenta Cansino", f"${ing_cansino:,.2f}")

    sc4, sc5 = st.columns(2)
    sc4.metric("Ingresado (Cuenta Llanez)", f"${ing_angel_cuenta:,.2f}")
    sc5.metric("Ingresado (Cuenta Montalvo)", f"${ing_montalvo_cuenta:,.2f}")

    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📈 Ingresos vs Egresos vs Utilidad Real")
        df_bar = pd.DataFrame({
            'Concepto': ['Ingresos (Subtotal)', 'Gastos + Costo Fiscal', 'Utilidad Neta Real'],
            'Monto': [subtotal_ingresos_reales, gastos_totales_mes + costo_fiscal_mes, utilidad_neta_real]
        })
        st.bar_chart(df_bar.set_index('Concepto'))
            
    with col_g2:
        st.subheader("📊 Facturación por Socio")
        df_soc = pd.DataFrame({
            'Socio': ['Angel Llanez', 'Adolfo Montalvo'],
            'Facturación': [fac_angel, fac_montalvo]
        })
        st.bar_chart(df_soc.set_index('Socio'))

# ==========================================
# PESTAÑA 2: TRABAJOS Y OPERACIONES
# ==========================================
with tab_trabajos:
    st.header("💼 Gestión de Trabajos y Operaciones")
    
    df_t_raw = pd.DataFrame(supabase.table("trabajos").select("*").execute().data)

    clientes_df = get_catalogo("cat_clientes")
    lista_clientes = clientes_df['nombre'].tolist() if not clientes_df.empty else ["Sin Clientes"]
    
    cats_df = get_catalogo("cat_categorias")
    lista_categorias = cats_df['nombre'].tolist() if not cats_df.empty else ["General"]
    
    subcats_df = get_catalogo("cat_subcategorias")
    lista_subcategorias = subcats_df['nombre'].tolist() if not subcats_df.empty else ["General"]
    
    cuentas_df = get_catalogo("cat_cuentas")
    lista_cuentas = ["-- Sin asignar --"] + (cuentas_df['nombre'].tolist() if not cuentas_df.empty else ["Efectivo"])
    
    equipos_db = get_equipos_catalogo_tuples()
    lista_equipos_strs = ["Sin equipo"] + ([f"Eco: {e[1]} | {e[2]} {e[3]} (Cliente: {e[5]})" for e in equipos_db] if equipos_db else [])

    with st.expander("➕ Registrar Nuevo Trabajo / Cotización", expanded=False):
        with st.form("form_trabajo", clear_on_submit=True):
            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1:
                fecha_t = st.date_input("Fecha", value=datetime.today())
                cliente = st.selectbox("Cliente", lista_clientes)
                equipo_sel = st.selectbox("Equipo", lista_equipos_strs)
                modelo = st.text_input("Modelo (Opcional)")
                serie = st.text_input("Serie (Opcional)")
            with tc2:
                categoria = st.selectbox("Categoría", lista_categorias)
                subcategoria = st.selectbox("Subcategoría", lista_subcategorias)
                descripcion = st.text_area("Descripción del Trabajo / Cotización")
                recibo_corr = st.text_input("Recibo Correctivo (Opcional)")
                recibo_prev = st.text_input("Recibo Preventivo (Opcional)")
            with tc3:
                estado_trabajo = st.selectbox("Estado de Trabajo", ["Pendiente", "En Proceso", "Terminado", "Entregado", "N/A (Cotización)"])
                estado_financiero = st.selectbox("Estado Financiero", ["Por Cotizar", "Cotizado", "Aprobado", "Facturado", "Pagado"])
                cotizacion = st.text_input("Cotización No. (Opcional)")
                fecha_cot = st.date_input("Fecha Cotización (Opcional)", value=None, key="fcot_add")
                oc = st.text_input("O.C. (Opcional)")
                fecha_oc = st.date_input("Fecha O.C. (Opcional)", value=None, key="foc_add")
            with tc4:
                factura = st.text_input("Factura (Opcional)")
                fecha_factura = st.date_input("Fecha Factura (Opcional)", value=None, key="ffactura_add")
                facturado_por = st.selectbox("Facturado Por", ["-- Pendiente / Sin facturar --", "Angel Llanez", "Adolfo Montalvo", "Externo"])
                subtotal = st.number_input("Subtotal ($)", min_value=0.0, step=0.01)
                iva = subtotal * 0.16
                total = subtotal + iva
                cuenta_dep = st.selectbox("Cuenta donde se depositó", lista_cuentas)
                estado_pago = st.selectbox("Estado de Pago", ["Pendiente", "Pagado", "Parcial"])
                fecha_pago = st.date_input("Fecha de Pago (Opcional)", value=None, key="fpago_add")
                portal = st.selectbox("Portal", ["Pendiente de Subir", "Sí", "No"])

            if st.form_submit_button("Guardar Registro en la Nube"):
                fecha_str = str(fecha_t)
                id_gen = generar_id("tr", fecha_str)
                eq_final = "" if equipo_sel == "Sin equipo" else equipo_sel
                
                f_cot_str = str(fecha_cot) if fecha_cot is not None else ""
                f_oc_str = str(fecha_oc) if fecha_oc is not None else ""
                f_factura_str = str(fecha_factura) if fecha_factura is not None else ""
                f_pago_str = str(fecha_pago) if fecha_pago is not None else ""
                
                fac_por_final = "" if facturado_por == "-- Pendiente / Sin facturar --" else facturado_por
                cta_final = "" if cuenta_dep == "-- Sin asignar --" else cuenta_dep
                
                data_trabajo = {
                    "id_personalizado": id_gen, "fecha": fecha_str, "cliente": cliente,
                    "equipo": eq_final, "modelo": modelo, "serie": serie, "categoria": categoria,
                    "subcategoria": subcategoria, "descripcion": descripcion,
                    "recibo_correctivo": recibo_corr, "recibo_preventivo": recibo_prev,
                    "estado_trabajo": estado_trabajo, "estado_financiero": estado_financiero,
                    "cotizacion": cotizacion, "fecha_cotizacion": f_cot_str, "oc": oc,
                    "fecha_oc": f_oc_str, "factura": factura, "fecha_factura": f_factura_str, 
                    "facturado_por": fac_por_final, "subtotal": float(subtotal), "iva": float(iva), 
                    "total": float(total), "cuenta_deposito": cta_final, "estado_pago": estado_pago,
                    "fecha_pago": f_pago_str, "portal": portal
                }
                
                try:
                    res = supabase.table("trabajos").insert(data_trabajo).execute()
                    st.success(f"¡Registro guardado con éxito! ID asignado: {id_gen}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error real al intentar guardar en Supabase: {str(e)}")
                    st.error(f"Datos intentados: {data_trabajo}")

    if not df_t_raw.empty:
        lista_ids = [str(x) for x in df_t_raw['id_personalizado'].tolist() if x is not None and str(x) != 'nan' and str(x) != '']
        with st.expander("✏️ Editar o 🗑️ Borrar Trabajo Existente", expanded=False):
            id_a_editar = st.selectbox("Selecciona el ID del Trabajo a Editar/Borrar", lista_ids)
            registro_actual = df_t_raw[df_t_raw['id_personalizado'] == id_a_editar].iloc[0]
            
            with st.form("form_editar_trabajo"):
                st.write(f"Editando Registro: **{id_a_editar}**")
                
                ec1, ec2, ec3, ec4 = st.columns(4)
                with ec1:
                    est_t_opts = ["Pendiente", "En Proceso", "Terminado", "Entregado", "N/A (Cotización)"]
                    val_t = str(registro_actual['estado_trabajo'])
                    idx_t = est_t_opts.index(val_t) if val_t in est_t_opts else 0
                    nuevo_estatus_t = st.selectbox("Estado de Trabajo", est_t_opts, index=idx_t)

                    est_f_opts = ["Por Cotizar", "Cotizado", "Aprobado", "Facturado", "Pagado"]
                    val_f = str(registro_actual['estado_financiero'])
                    idx_f = est_f_opts.index(val_f) if val_f in est_f_opts else 0
                    nuevo_estatus_f = st.selectbox("Estado Financiero", est_f_opts, index=idx_f)

                    est_p_opts = ["Pendiente", "Pagado", "Parcial"]
                    val_p = str(registro_actual['estado_pago'])
                    idx_p = est_p_opts.index(val_p) if val_p in est_p_opts else 0
                    nuevo_estatus_p = st.selectbox("Estado de Pago", est_p_opts, index=idx_p)
                
                with ec2:
                    val_cot_txt = str(registro_actual['cotizacion']) if pd.notna(registro_actual['cotizacion']) else ""
                    nueva_cotizacion = st.text_input("Cotización No.", value=val_cot_txt)
                    
                    val_oc_txt = str(registro_actual['oc']) if pd.notna(registro_actual['oc']) else ""
                    nueva_oc = st.text_input("O.C.", value=val_oc_txt)
                    
                    val_factura_txt = str(registro_actual['factura']) if pd.notna(registro_actual['factura']) else ""
                    nueva_factura = st.text_input("Factura No.", value=val_factura_txt)

                with ec3:
                    val_fcot_ant = str(registro_actual.get('fecha_cotizacion', '')) if pd.notna(registro_actual.get('fecha_cotizacion', '')) and str(registro_actual.get('fecha_cotizacion', '')).strip() != '' else None
                    dt_fcot = datetime.strptime(val_fcot_ant, "%Y-%m-%d").date() if val_fcot_ant else None
                    nueva_fecha_cot = st.date_input("Fecha Cotización", value=dt_fcot, key="fcot_edit")

                    val_foc_ant = str(registro_actual.get('fecha_oc', '')) if pd.notna(registro_actual.get('fecha_oc', '')) and str(registro_actual.get('fecha_oc', '')).strip() != '' else None
                    dt_foc = datetime.strptime(val_foc_ant, "%Y-%m-%d").date() if val_foc_ant else None
                    nueva_fecha_oc = st.date_input("Fecha O.C.", value=dt_foc, key="foc_edit")

                    val_ffac_ant = str(registro_actual.get('fecha_factura', '')) if pd.notna(registro_actual.get('fecha_factura', '')) and str(registro_actual.get('fecha_factura', '')).strip() != '' else None
                    dt_ffac = datetime.strptime(val_ffac_ant, "%Y-%m-%d").date() if val_ffac_ant else None
                    nueva_fecha_factura = st.date_input("Fecha Factura", value=dt_ffac, key="ffactura_edit")

                    val_fp_ant = str(registro_actual.get('fecha_pago', '')) if pd.notna(registro_actual.get('fecha_pago', '')) and str(registro_actual.get('fecha_pago', '')).strip() != '' else None
                    dt_fp = datetime.strptime(val_fp_ant, "%Y-%m-%d").date() if val_fp_ant else None
                    nueva_fecha_pago = st.date_input("Fecha de Pago", value=dt_fp, key="fpago_edit")

                with ec4:
                    fac_opts = ["-- Pendiente / Sin facturar --", "Angel Llanez", "Adolfo Montalvo", "Externo"]
                    val_fac = str(registro_actual['facturado_por']) if pd.notna(registro_actual['facturado_por']) and registro_actual['facturado_por'] != '' else "-- Pendiente / Sin facturar --"
                    idx_fac = fac_opts.index(val_fac) if val_fac in fac_opts else 0
                    nuevo_fac_por = st.selectbox("Facturado Por", fac_opts, index=idx_fac)

                    val_cta = str(registro_actual['cuenta_deposito']) if pd.notna(registro_actual['cuenta_deposito']) and str(registro_actual['cuenta_deposito']).strip() != '' else "-- Sin asignar --"
                    idx_cta = lista_cuentas.index(val_cta) if val_cta in lista_cuentas else 0
                    nueva_cuenta = st.selectbox("Cuenta donde se depositó", lista_cuentas, index=idx_cta)

                    portal_opts = ["Pendiente de Subir", "Sí", "No"]
                    val_portal = str(registro_actual['portal']) if pd.notna(registro_actual['portal']) else "Pendiente de Subir"
                    idx_portal = portal_opts.index(val_portal) if val_portal in portal_opts else 0
                    nuevo_portal = st.selectbox("Portal", portal_opts, index=idx_portal)

                    sub_val_ant = float(registro_actual['subtotal']) if pd.notna(registro_actual['subtotal']) else 0.0
                    nuevo_subtotal = st.number_input("Subtotal ($)", value=sub_val_ant, step=0.01)
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("💾 Guardar Cambios"):
                    nuevo_iva = float(nuevo_subtotal) * 0.16
                    nuevo_total = float(nuevo_subtotal) + nuevo_iva
                    fac_por_fin = "" if nuevo_fac_por == "-- Pendiente / Sin facturar --" else nuevo_fac_por
                    cta_fin = "" if nueva_cuenta == "-- Sin asignar --" else nueva_cuenta
                    
                    f_cot_fin = str(nueva_fecha_cot) if nueva_fecha_cot is not None else ""
                    f_oc_fin = str(nueva_fecha_oc) if nueva_fecha_oc is not None else ""
                    f_factura_fin = str(nueva_fecha_factura) if nueva_fecha_factura is not None else ""
                    f_pago_fin = str(nueva_fecha_pago) if nueva_fecha_pago is not None else ""
                    
                    update_data = {
                        "estado_trabajo": nuevo_estatus_t, "estado_financiero": nuevo_estatus_f, 
                        "estado_pago": nuevo_estatus_p, "cotizacion": nueva_cotizacion, 
                        "oc": nueva_oc, "factura": nueva_factura, "facturado_por": fac_por_fin, 
                        "cuenta_deposito": cta_fin, "portal": nuevo_portal, 
                        "subtotal": float(nuevo_subtotal), "iva": float(nuevo_iva), 
                        "total": float(nuevo_total), "fecha_cotizacion": f_cot_fin, 
                        "fecha_oc": f_oc_fin, "fecha_factura": f_factura_fin, "fecha_pago": f_pago_fin
                    }
                    
                    try:
                        supabase.table("trabajos").update(update_data).eq("id_personalizado", id_a_editar).execute()
                        st.success("¡Trabajo actualizado con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al actualizar: {str(e)}")
                    
                if col_btn2.form_submit_button("🗑️ Eliminar Trabajo"):
                    supabase.table("trabajos").delete().eq("id_personalizado", id_a_editar).execute()
                    st.warning("Trabajo eliminado.")
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 Historial de Trabajos")
    if not df_t_raw.empty:
        df_hist = df_t_raw.copy()
        df_hist['fecha_dt'] = pd.to_datetime(df_hist['fecha'], errors='coerce')
        
        col_f1, col_f2 = st.columns(2)
        anos_hist = sorted(list(set([str(int(y)) for y in df_hist['fecha_dt'].dt.year.dropna().unique()] + [str(datetime.now().year)])))
        anio_filtro = col_f1.selectbox("Filtrar por Año", anos_hist, index=len(anos_hist)-1, key="hist_anio")
        
        meses_hist = ["Todos", "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio", 
                      "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"]
        mes_filtro = col_f2.selectbox("Filtrar por Mes", meses_hist, index=0, key="hist_mes")
        
        df_hist = df_hist[df_hist['fecha_dt'].dt.year == int(anio_filtro)]
        if mes_filtro != "Todos":
            num_mes_filtro = int(mes_filtro.split(" - ")[0])
            df_hist = df_hist[df_hist['fecha_dt'].dt.month == num_mes_filtro]
            
        if df_hist.empty:
            st.info("No hay trabajos en el mes seleccionado.")
        else:
            df_display = df_hist.drop(columns=['fecha_dt'])
            st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No hay trabajos registrados todavía.")

# ==========================================
# PESTAÑA 3: GASTOS Y TRAZABILIDAD
# ==========================================
with tab_gastos:
    st.header("💸 Gastos y Trazabilidad por Trabajo")
    
    df_g_raw = pd.DataFrame(supabase.table("gastos").select("*").execute().data)

    clientes_df = get_catalogo("cat_clientes")
    lista_clientes = clientes_df['nombre'].tolist() if not clientes_df.empty else ["Sin Clientes"]
    
    cats_df = get_catalogo("cat_categorias")
    lista_categorias = cats_df['nombre'].tolist() if not cats_df.empty else ["General"]
    
    subcats_df = get_catalogo("cat_subcategorias")
    lista_subcategorias = subcats_df['nombre'].tolist() if not subcats_df.empty else ["General"]
    
    cuentas_df = get_catalogo("cat_cuentas")
    lista_cuentas = ["-- Sin asignar --"] + (cuentas_df['nombre'].tolist() if not cuentas_df.empty else ["Efectivo"])
    
    provs_df = get_catalogo("cat_proveedores")
    lista_proveedores = provs_df['nombre'].tolist() if not provs_df.empty else ["Sin Proveedores"]
    
    equipos_db = get_equipos_catalogo_tuples()
    lista_equipos_strs = ["Sin equipo"] + ([f"Eco: {e[1]} | {e[2]} {e[3]} (Cliente: {e[5]})" for e in equipos_db] if equipos_db else [])
    
    t_list = pd.DataFrame(supabase.table("trabajos").select("id_personalizado, cliente, equipo").execute().data)
    trabajos_opciones = ["Ninguno"] + [f"{r['id_personalizado']} - {r['cliente']} ({r['equipo']})" for _, r in t_list.iterrows()] if not t_list.empty else ["Ninguno"]

    with st.expander("➕ Registrar Nuevo Gasto", expanded=False):
        with st.form("form_gasto", clear_on_submit=True):
            gc1, gc2, gc3 = st.columns(3)
            with gc1:
                fecha_g = st.date_input("Fecha Gasto", value=datetime.today())
                cliente_g = st.selectbox("Cliente Relacionado", lista_clientes)
                equipo_g = st.selectbox("Equipo Relacionado", lista_equipos_strs)
                categoria_g = st.selectbox("Categoría de Gasto", lista_categorias)
            with gc2:
                subcategoria_g = st.selectbox("Subcategoría Gasto", lista_subcategorias)
                proveedor_g = st.selectbox("Proveedor", lista_proveedores)
                trabajo_rel = st.selectbox("Trabajo Relacionado (Trazabilidad)", trabajos_opciones)
            with gc3:
                folio_ticket = st.text_input("Folio de Ticket o Factura")
                metodo_pago = st.selectbox("Método de Pago", ["Transferencia", "Efectivo", "Tarjeta"])
                cuenta_g = st.selectbox("Cuenta Gasto", lista_cuentas)
                sub_g = st.number_input("Subtotal Gasto ($)", min_value=0.0, step=0.01)
                iva_g = sub_g * 0.16
                tot_g = sub_g + iva_g

            desc_g = st.text_area("Descripción / Detalle del Gasto")
            if st.form_submit_button("Guardar Gasto"):
                fecha_str = str(fecha_g)
                id_gen_g = generar_id("ga", fecha_str)
                eq_g_final = "" if equipo_g == "Sin equipo" else equipo_g
                cta_g_final = "" if cuenta_g == "-- Sin asignar --" else cuenta_g
                tr_g_final = "" if trabajo_rel == "Ninguno" else trabajo_rel
                
                gasto_data = {
                    "id_personalizado": id_gen_g, "fecha": fecha_str, "cliente": cliente_g,
                    "equipo": eq_g_final, "categoria": categoria_g, "subcategoria": subcategoria_g,
                    "proveedor": proveedor_g, "trabajo_relacionado": tr_g_final, "descripcion": desc_g,
                    "folio_ticket": folio_ticket, "metodo_pago": metodo_pago, "cuenta": cta_g_final,
                    "subtotal": float(sub_g), "iva": float(iva_g), "total": float(tot_g)
                }
                
                try:
                    supabase.table("gastos").insert(gasto_data).execute()
                    st.success(f"¡Gasto registrado con éxito! ID: {id_gen_g}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar gasto en Supabase: {str(e)}")

    if not df_g_raw.empty:
        lista_ids_g = [str(x) for x in df_g_raw['id_personalizado'].tolist() if x is not None and str(x) != 'nan' and str(x) != '']
        with st.expander("✏️ Editar o 🗑️ Borrar Gasto Existente", expanded=False):
            id_g_editar = st.selectbox("Selecciona el ID del Gasto a Editar/Borrar", lista_ids_g)
            reg_g_actual = df_g_raw[df_g_raw['id_personalizado'] == id_g_editar].iloc[0]
            
            with st.form("form_editar_gasto"):
                st.write(f"Editando Gasto: **{id_g_editar}**")
                
                egc1, egc2, egc3 = st.columns(3)
                with egc1:
                    val_cli = str(reg_g_actual.get('cliente', ''))
                    idx_cli = lista_clientes.index(val_cli) if val_cli in lista_clientes else 0
                    n_cliente_g = st.selectbox("Cliente Relacionado", lista_clientes, index=idx_cli)
                    
                    val_eq = str(reg_g_actual.get('equipo', ''))
                    idx_eq = lista_equipos_strs.index(val_eq) if val_eq in lista_equipos_strs else 0
                    n_equipo_g = st.selectbox("Equipo Relacionado", lista_equipos_strs, index=idx_eq)
                    
                    val_cat = str(reg_g_actual.get('categoria', ''))
                    idx_cat = lista_categorias.index(val_cat) if val_cat in lista_categorias else 0
                    n_categoria_g = st.selectbox("Categoría de Gasto", lista_categorias, index=idx_cat)
                    
                with egc2:
                    val_subcat = str(reg_g_actual.get('subcategoria', ''))
                    idx_subcat = lista_subcategorias.index(val_subcat) if val_subcat in lista_subcategorias else 0
                    n_subcategoria_g = st.selectbox("Subcategoría Gasto", lista_subcategorias, index=idx_subcat)
                    
                    val_prov = str(reg_g_actual.get('proveedor', ''))
                    idx_prov = lista_proveedores.index(val_prov) if val_prov in lista_proveedores else 0
                    n_proveedor_g = st.selectbox("Proveedor", lista_proveedores, index=idx_prov)
                    
                    val_tr = str(reg_g_actual.get('trabajo_relacionado', ''))
                    idx_tr = trabajos_opciones.index(val_tr) if val_tr in trabajos_opciones else 0
                    n_trabajo_rel = st.selectbox("Trabajo Relacionado", trabajos_opciones, index=idx_tr)
                    
                with egc3:
                    val_folio = str(reg_g_actual.get('folio_ticket', '')) if pd.notna(reg_g_actual.get('folio_ticket')) else ""
                    n_folio_ticket = st.text_input("Folio de Ticket o Factura", value=val_folio)
                    
                    metodos_pago = ["Transferencia", "Efectivo", "Tarjeta"]
                    val_mp = str(reg_g_actual.get('metodo_pago', ''))
                    idx_mp = metodos_pago.index(val_mp) if val_mp in metodos_pago else 0
                    n_metodo_pago = st.selectbox("Método de Pago", metodos_pago, index=idx_mp)
                    
                    val_cta = str(reg_g_actual.get('cuenta', ''))
                    idx_cta = lista_cuentas.index(val_cta) if val_cta in lista_cuentas else 0
                    n_cuenta_g = st.selectbox("Cuenta Gasto", lista_cuentas, index=idx_cta)
                    
                n_sub_g = st.number_input("Subtotal Gasto ($)", value=float(reg_g_actual.get('subtotal', 0.0)), step=0.01)
                val_desc = str(reg_g_actual.get('descripcion', '')) if pd.notna(reg_g_actual.get('descripcion')) else ""
                n_desc_g = st.text_area("Descripción / Detalle del Gasto", value=val_desc)
                
                col_btn_g1, col_btn_g2 = st.columns(2)
                if col_btn_g1.form_submit_button("💾 Guardar Cambios"):
                    n_iva_g = float(n_sub_g) * 0.16
                    n_tot_g = float(n_sub_g) + n_iva_g
                    
                    eq_g_fin = "" if n_equipo_g == "Sin equipo" else n_equipo_g
                    cta_g_fin = "" if n_cuenta_g == "-- Sin asignar --" else n_cuenta_g
                    tr_g_fin = "" if n_trabajo_rel == "Ninguno" else n_trabajo_rel
                    
                    update_g_data = {
                        "cliente": n_cliente_g, "equipo": eq_g_fin, "categoria": n_categoria_g,
                        "subcategoria": n_subcategoria_g, "proveedor": n_proveedor_g,
                        "trabajo_relacionado": tr_g_fin, "folio_ticket": n_folio_ticket,
                        "metodo_pago": n_metodo_pago, "cuenta": cta_g_fin,
                        "subtotal": float(n_sub_g), "iva": float(n_iva_g), "total": float(n_tot_g),
                        "descripcion": n_desc_g
                    }
                    
                    try:
                        supabase.table("gastos").update(update_g_data).eq("id_personalizado", id_g_editar).execute()
                        st.success("¡Gasto actualizado con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al actualizar gasto: {str(e)}")
                        
                if col_btn_g2.form_submit_button("🗑️ Eliminar Gasto"):
                    supabase.table("gastos").delete().eq("id_personalizado", id_g_editar).execute()
                    st.warning("Gasto eliminado.")
                    st.rerun()

    st.markdown("---")
    st.subheader("📊 Historial de Gastos")
    if not df_g_raw.empty:
        df_g_hist = df_g_raw.copy()
        df_g_hist['fecha_dt'] = pd.to_datetime(df_g_hist['fecha'], errors='coerce')
        
        col_gf1, col_gf2 = st.columns(2)
        anos_g_hist = sorted(list(set([str(int(y)) for y in df_g_hist['fecha_dt'].dt.year.dropna().unique()] + [str(datetime.now().year)])))
        anio_g_filtro = col_gf1.selectbox("Filtrar por Año", anos_g_hist, index=len(anos_g_hist)-1, key="hist_g_anio")
        
        mes_g_filtro = col_gf2.selectbox("Filtrar por Mes", meses_nombres, index=0, key="hist_g_mes")
        
        df_g_hist = df_g_hist[df_g_hist['fecha_dt'].dt.year == int(anio_g_filtro)]
        if mes_g_filtro != "Todos":
            num_mes_g_filtro = int(mes_g_filtro.split(" - ")[0])
            df_g_hist = df_g_hist[df_g_hist['fecha_dt'].dt.month == num_mes_g_filtro]
            
        if df_g_hist.empty:
            st.info("No hay gastos en el mes seleccionado.")
        else:
            df_g_display = df_g_hist.drop(columns=['fecha_dt'])
            st.dataframe(df_g_display, use_container_width=True)
    else:
        st.info("No hay gastos registrados todavía.")

# ==========================================
# PESTAÑA 4: MÓDULO DE RENTAS
# ==========================================
with tab_rentas:
    st.header("🛞 Módulo de Control de Rentas")
    
    df_rentas = pd.DataFrame(supabase.table("rentas").select("*").execute().data)
    
    with st.expander("➕ Registrar Nueva Renta", expanded=False):
        with st.form("form_renta", clear_on_submit=True):
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                cli_renta = st.selectbox("Cliente", lista_clientes, key="cli_r")
                eq_renta = st.selectbox("Equipo Rentado", lista_equipos_strs, key="eq_r")
            with rc2:
                f_inicio = st.date_input("Fecha de Inicio", value=datetime.today())
                f_fin = st.date_input("Fecha de Vencimiento / Próximo Pago", value=datetime.today() + timedelta(days=30))
            with rc3:
                monto_renta = st.number_input("Monto de la Renta ($ Subtotal)", min_value=0.0, step=0.01)
                estado_renta = st.selectbox("Estatus de Renta", ["Activa", "Vencida", "Finalizada"])
                
            if st.form_submit_button("Guardar Renta"):
                fecha_str = str(datetime.today().date())
                id_r = generar_id("rt", fecha_str)
                eq_r_final = "" if eq_renta == "Sin equipo" else eq_renta
                
                renta_data = {
                    "id_personalizado": id_r, "cliente": cli_renta, "equipo": eq_r_final,
                    "fecha_inicio": str(f_inicio), "fecha_fin": str(f_fin), 
                    "monto": float(monto_renta), "estado": estado_renta
                }
                
                supabase.table("rentas").insert(renta_data).execute()
                st.success(f"¡Renta registrada con éxito! ID: {id_r}")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Listado de Rentas Activas y Alertas")
    
    if not df_rentas.empty:
        hoy = datetime.now().date()
        for idx, row in df_rentas.iterrows():
            f_venc = datetime.strptime(row['fecha_fin'], "%Y-%m-%d").date()
            dias_restantes = (f_venc - hoy).days
            
            badge = ""
            if row['estado'] == "Activa":
                if dias_restantes < 0:
                    badge = "🔴 **[VENCIDA]**"
                elif dias_restantes <= 7:
                    badge = f"⚠️ **[Vence en {dias_restantes} días]**"
                else:
                    badge = "🟢 **[Al corriente]**"
            else:
                badge = f"⚪ **[{row['estado']}]**"
                
            with st.expander(f"{row['id_personalizado']} | Cliente: {row['cliente']} | Equipo: {row['equipo']} | Monto: ${row['monto']:,.2f} {badge}"):
                st.write(f"• **Fecha Inicio:** {row['fecha_inicio']}")
                st.write(f"• **Fecha Vencimiento:** {row['fecha_fin']}")
                st.write(f"• **Monto Subtotal:** ${row['monto']:,.2f}")
                
                col_ra1, col_ra2 = st.columns(2)
                if col_ra1.button("⚡ Generar Trabajo / Cotización de Renta", key=f"gen_trab_{row['id_personalizado']}"):
                    fecha_hoy_str = str(datetime.today().date())
                    id_nuevo_trabajo = generar_id("tr", fecha_hoy_str)
                    subt = float(row['monto'])
                    iva_t = subt * 0.16
                    tot_t = subt + iva_t
                    desc_trabajo = f"Renta mensual de equipo {row['equipo']} correspondiente al periodo {row['fecha_inicio']} al {row['fecha_fin']}"
                    
                    data_trab_renta = {
                        "id_personalizado": id_nuevo_trabajo, "fecha": fecha_hoy_str, 
                        "cliente": row['cliente'], "equipo": row['equipo'], 
                        "categoria": "Renta", "subcategoria": "Renta Mensual", 
                        "descripcion": desc_trabajo, "estado_trabajo": "Pendiente", 
                        "estado_financiero": "Por Cotizar", "subtotal": subt, 
                        "iva": iva_t, "total": tot_t, "estado_pago": "Pendiente"
                    }
                    
                    supabase.table("trabajos").insert(data_trab_renta).execute()
                    st.success(f"¡Trabajo generado con éxito en Trabajos y Operaciones con ID: {id_nuevo_trabajo}!")
                
                if col_ra2.button("🗑️ Borrar Renta", key=f"del_renta_{row['id_personalizado']}"):
                    supabase.table("rentas").delete().eq("id_personalizado", row['id_personalizado']).execute()
                    st.warning("Renta eliminada.")
                    st.rerun()
    else:
        st.info("No hay rentas registradas en el sistema.")

# ==========================================
# PESTAÑA 5: CONFIGURACIÓN Y CATÁLOGOS MAESTROS
# ==========================================
with tab_config:
    st.header("⚙️ Configuración y Catálogos Maestros")
    
    capital_actual = get_capital_inicial()
    new_cap = st.number_input("Establecer Capital Inicial del ERP ($)", value=capital_actual, step=1000.0)
    if st.button("Actualizar Capital Inicial"):
        set_capital_inicial(new_cap)
        st.success("¡Capital inicial actualizado correctamente!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("🗂️ Gestión de Catálogos del Sistema")

    sub_cat_tab1, sub_cat_tab2, sub_cat_tab3, sub_cat_tab4, sub_cat_tab5, sub_cat_tab6 = st.tabs([
        "🏢 Clientes", "🚜 Equipos", "🏷️ Categorías", "📂 Subcategorías", "🤝 Proveedores", "💳 Cuentas"
    ])

    clients_df_tab = get_catalogo("cat_clientes")
    clients_for_eq = clients_df_tab['nombre'].tolist() if not clients_df_tab.empty else ["General"]

    # 1. CLIENTES
    with sub_cat_tab1:
        with st.expander("➕ Agregar Nuevo Cliente", expanded=False):
            with st.form("add_cli", clear_on_submit=True):
                nuevo_cli = st.text_input("Nombre del Nuevo Cliente")
                if st.form_submit_button("Agregar Cliente"):
                    if nuevo_cli.strip():
                        try:
                            supabase.table("cat_clientes").insert({"nombre": nuevo_cli.strip()}).execute()
                            st.success("¡Cliente agregado!")
                            st.rerun()
                        except Exception: st.error("El cliente ya existe o hubo un error.")
        
        st.markdown("---")
        with st.expander("📋 Ver y Editar Clientes Registrados", expanded=False):
            if not clients_df_tab.empty:
                for _, row_c in clients_df_tab.iterrows():
                    cid, cname = row_c['id'], row_c['nombre']
                    with st.expander(f"Cliente: {cname}"):
                        with st.form(f"form_edit_cli_{cid}"):
                            edit_cname = st.text_input("Modificar Nombre", value=cname)
                            col_eb1, col_eb2 = st.columns(2)
                            if col_eb1.form_submit_button("💾 Guardar"):
                                supabase.table("cat_clientes").update({"nombre": edit_cname.strip()}).eq("id", cid).execute()
                                st.success("¡Actualizado!")
                                st.rerun()
                            if col_eb2.form_submit_button("🗑️ Borrar"):
                                supabase.table("cat_clientes").delete().eq("id", cid).execute()
                                st.rerun()

    # 2. EQUIPOS
    with sub_cat_tab2:
        with st.expander("➕ Registrar Nuevo Equipo", expanded=False):
            with st.form("add_equipo_form_master_nube", clear_on_submit=True):
                eq_eco = st.text_input("Número Económico / Identificador (Opcional)")
                eq_marca = st.text_input("Marca (Ej. Mitsubishi, Toyota)")
                eq_modelo = st.text_input("Modelo")
                eq_serie = st.text_input("Serie")
                eq_cliente = st.selectbox("Cliente Asociado / Propio", clients_for_eq)
                
                if st.form_submit_button("Registrar Nuevo Equipo"):
                    eco_final = eq_eco.strip() if eq_eco.strip() else "S/N"
                    supabase.table("cat_equipos").insert({
                        "eco": eco_final, "marca": eq_marca.strip(), 
                        "modelo": eq_modelo.strip(), "serie": eq_serie.strip(), "cliente": eq_cliente
                    }).execute()
                    st.success("¡Equipo registrado en la Nube correctamente!")
                    st.rerun()
        
        st.markdown("---")
        with st.expander("📋 Ver y Editar Equipos Registrados", expanded=False):
            eqs_df_tab = get_equipos_catalogo_df()
            if not eqs_df_tab.empty:
                for _, e in eqs_df_tab.iterrows():
                    eq_id = e['id']
                    eco_display = e['eco'] if pd.notna(e['eco']) and str(e['eco']).strip() != "" else "S/N"
                    with st.expander(f"Eco: {eco_display} | {e['marca']} {e['modelo']} — Cliente: {e['cliente']}"):
                        with st.form(f"form_edit_eq_{eq_id}"):
                            ed_eco = st.text_input("Número Económico", value=str(e['eco']) if pd.notna(e['eco']) else "")
                            ed_marca = st.text_input("Marca", value=str(e['marca']) if pd.notna(e['marca']) else "")
                            ed_modelo = st.text_input("Modelo", value=str(e['modelo']) if pd.notna(e['modelo']) else "")
                            ed_serie = st.text_input("Serie", value=str(e['serie']) if pd.notna(e['serie']) else "")
                            
                            idx_cli = clients_for_eq.index(e['cliente']) if e['cliente'] in clients_for_eq else 0
                            ed_cli = st.selectbox("Cliente", clients_for_eq, index=idx_cli, key=f"sel_cli_eq_{eq_id}")
                            
                            col_eq1, col_eq2 = st.columns(2)
                            if col_eq1.form_submit_button("💾 Guardar"):
                                eco_edit_final = ed_eco.strip() if ed_eco.strip() else "S/N"
                                supabase.table("cat_equipos").update({
                                    "eco": eco_edit_final, "marca": ed_marca.strip(), 
                                    "modelo": ed_modelo.strip(), "serie": ed_serie.strip(), "cliente": ed_cli
                                }).eq("id", eq_id).execute()
                                st.success("¡Equipo actualizado!")
                                st.rerun()
                            if col_eq2.form_submit_button("🗑️ Borrar"):
                                supabase.table("cat_equipos").delete().eq("id", eq_id).execute()
                                st.rerun()

    # 3. CATEGORÍAS
    with sub_cat_tab3:
        with st.expander("➕ Agregar Nueva Categoría", expanded=False):
            with st.form("add_cat", clear_on_submit=True):
                n_cat = st.text_input("Nueva Categoría")
                if st.form_submit_button("Agregar Categoría"):
                    if n_cat.strip():
                        try:
                            supabase.table("cat_categorias").insert({"nombre": n_cat.strip()}).execute()
                            st.rerun()
                        except Exception: st.error("Ya existe.")
        st.markdown("---")
        with st.expander("📋 Ver y Editar Categorías Registradas", expanded=False):
            cats_df_tab = get_catalogo("cat_categorias")
            if not cats_df_tab.empty:
                for _, row_cat in cats_df_tab.iterrows():
                    cid, cname = row_cat['id'], row_cat['nombre']
                    with st.expander(f"Categoría: {cname}"):
                        with st.form(f"form_edit_cat_{cid}"):
                            ed_cname = st.text_input("Modificar", value=cname)
                            cb1, cb2 = st.columns(2)
                            if cb1.form_submit_button("💾 Guardar"):
                                supabase.table("cat_categorias").update({"nombre": ed_cname.strip()}).eq("id", cid).execute()
                                st.rerun()
                            if cb2.form_submit_button("🗑️ Borrar"):
                                supabase.table("cat_categorias").delete().eq("id", cid).execute()
                                st.rerun()

    # 4. SUBCATEGORÍAS
    with sub_cat_tab4:
        with st.expander("➕ Agregar Nueva Subcategoría", expanded=False):
            with st.form("add_subcat", clear_on_submit=True):
                n_sub = st.text_input("Nueva Subcategoría")
                if st.form_submit_button("Agregar Subcategoría"):
                    if n_sub.strip():
                        try:
                            supabase.table("cat_subcategorias").insert({"nombre": n_sub.strip()}).execute()
                            st.rerun()
                        except Exception: st.error("Ya existe.")
        st.markdown("---")
        with st.expander("📋 Ver y Editar Subcategorías Registradas", expanded=False):
            sub_df_tab = get_catalogo("cat_subcategorias")
            if not sub_df_tab.empty:
                for _, row_sub in sub_df_tab.iterrows():
                    cid, cname = row_sub['id'], row_sub['nombre']
                    with st.expander(f"Subcategoría: {cname}"):
                        with st.form(f"form_edit_subcat_{cid}"):
                            ed_sname = st.text_input("Modificar", value=cname)
                            sb1, sb2 = st.columns(2)
                            if sb1.form_submit_button("💾 Guardar"):
                                supabase.table("cat_subcategorias").update({"nombre": ed_sname.strip()}).eq("id", cid).execute()
                                st.rerun()
                            if sb2.form_submit_button("🗑️ Borrar"):
                                supabase.table("cat_subcategorias").delete().eq("id", cid).execute()
                                st.rerun()

    # 5. PROVEEDORES
    with sub_cat_tab5:
        with st.expander("➕ Agregar Nuevo Proveedor", expanded=False):
            with st.form("add_prov", clear_on_submit=True):
                n_prov = st.text_input("Nombre del Proveedor")
                if st.form_submit_button("Agregar Proveedor"):
                    if n_prov.strip():
                        try:
                            supabase.table("cat_proveedores").insert({"nombre": n_prov.strip()}).execute()
                            st.rerun()
                        except Exception: st.error("Ya existe.")
        st.markdown("---")
        with st.expander("📋 Ver y Editar Proveedores Registradas", expanded=False):
            prov_df_tab = get_catalogo("cat_proveedores")
            if not prov_df_tab.empty:
                for _, row_p in prov_df_tab.iterrows():
                    cid, cname = row_p['id'], row_p['nombre']
                    with st.expander(f"Proveedor: {cname}"):
                        with st.form(f"form_edit_prov_{cid}"):
                            ed_pname = st.text_input("Modificar", value=cname)
                            pb1, pb2 = st.columns(2)
                            if pb1.form_submit_button("💾 Guardar"):
                                supabase.table("cat_proveedores").update({"nombre": ed_pname.strip()}).eq("id", cid).execute()
                                st.rerun()
                            if pb2.form_submit_button("🗑️ Borrar"):
                                supabase.table("cat_proveedores").delete().eq("id", cid).execute()
                                st.rerun()

    # 6. CUENTAS
    with sub_cat_tab6:
        with st.expander("➕ Agregar Nueva Cuenta", expanded=False):
            with st.form("add_cta", clear_on_submit=True):
                n_cta = st.text_input("Nombre de la Cuenta o Método")
                if st.form_submit_button("Agregar Cuenta"):
                    if n_cta.strip():
                        try:
                            supabase.table("cat_cuentas").insert({"nombre": n_cta.strip()}).execute()
                            st.rerun()
                        except Exception: st.error("Ya existe.")
        st.markdown("---")
        with st.expander("📋 Ver y Editar Cuentas Registradas", expanded=False):
            cta_df_tab = get_catalogo("cat_cuentas")
            if not cta_df_tab.empty:
                for _, row_cta in cta_df_tab.iterrows():
                    cid, cname = row_cta['id'], row_cta['nombre']
                    with st.expander(f"Cuenta: {cname}"):
                        with st.form(f"form_edit_cta_{cid}"):
                            ed_cname = st.text_input("Modificar", value=cname)
                            cb1, cb2 = st.columns(2)
                            if cb1.form_submit_button("💾 Guardar"):
                                supabase.table("cat_cuentas").update({"nombre": ed_cname.strip()}).eq("id", cid).execute()
                                st.rerun()
                            if cb2.form_submit_button("🗑️ Borrar"):
                                supabase.table("cat_cuentas").delete().eq("id", cid).execute()
                                st.rerun()
