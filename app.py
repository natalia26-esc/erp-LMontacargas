import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import io

# Configuración de la página
st.set_page_config(page_title="ERP Montacargas - Control Financiero", layout="wide")

def init_db():
    conn = sqlite3.connect('erp_montacargas.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trabajos (
            id_personalizado TEXT PRIMARY KEY,
            fecha TEXT NOT NULL,
            cliente TEXT NOT NULL,
            equipo TEXT,
            modelo TEXT,
            serie TEXT,
            categoria TEXT,
            subcategoria TEXT,
            descripcion TEXT,
            recibo_correctivo TEXT,
            recibo_preventivo TEXT,
            estado_trabajo TEXT,
            estado_financiero TEXT,
            cotizacion TEXT,
            fecha_cotizacion TEXT,
            oc TEXT,
            fecha_oc TEXT,
            factura TEXT,
            fecha_factura TEXT,
            facturado_por TEXT,
            subtotal REAL,
            iva REAL,
            total REAL,
            cuenta_deposito TEXT,
            costo_fiscal REAL,
            ingreso_neto REAL,
            no_entrada TEXT,
            fecha_entrada TEXT,
            portal TEXT,
            fecha_portal TEXT,
            estado_pago TEXT,
            fecha_pago TEXT,
            fecha_pago_contador TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id_personalizado TEXT PRIMARY KEY,
            fecha TEXT NOT NULL,
            cliente TEXT,
            equipo TEXT,
            categoria TEXT,
            subcategoria TEXT,
            proveedor TEXT,
            trabajo_relacionado TEXT,
            descripcion TEXT,
            folio_ticket TEXT,
            metodo_pago TEXT,
            cuenta TEXT,
            subtotal REAL,
            iva REAL,
            total REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rentas (
            id_personalizado TEXT PRIMARY KEY,
            cliente TEXT NOT NULL,
            equipo TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            monto REAL NOT NULL,
            estado TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY,
            valor REAL
        )
    ''')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS cat_clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS cat_equipos (id INTEGER PRIMARY KEY AUTOINCREMENT, eco TEXT, marca TEXT, modelo TEXT, serie TEXT, cliente TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS cat_categorias (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS cat_subcategorias (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS cat_proveedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS cat_cuentas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL)')
    
    cursor.execute("SELECT COUNT(*) FROM cat_categorias")
    if cursor.fetchone()[0] == 0:
        for c in ["Mantenimiento", "Venta", "Renta", "Refacción", "Servicio Correctivo", "Servicio Preventivo"]:
            cursor.execute("INSERT OR IGNORE INTO cat_categorias (nombre) VALUES (?)", (c,))
            
    cursor.execute("SELECT COUNT(*) FROM cat_cuentas")
    if cursor.fetchone()[0] == 0:
        for cu in ["Cuenta Llanez", "Cuenta Montalvo", "Efectivo", "Cansino"]:
            cursor.execute("INSERT OR IGNORE INTO cat_cuentas (nombre) VALUES (?)", (cu,))
            
    conn.commit()
    conn.close()

init_db()

def get_catalogo(tabla):
    conn = sqlite3.connect('erp_montacargas.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {tabla}")
    res = cursor.fetchall()
    cols = [description[0] for description in cursor.description]
    conn.close()
    return pd.DataFrame(res, columns=cols) if res else pd.DataFrame()

def get_equipos_catalogo_df():
    conn = sqlite3.connect('erp_montacargas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cat_equipos")
    res = cursor.fetchall()
    cols = [description[0] for description in cursor.description]
    conn.close()
    return pd.DataFrame(res, columns=cols) if res else pd.DataFrame()

def get_equipos_catalogo_tuples():
    conn = sqlite3.connect('erp_montacargas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, eco, marca, modelo, serie, cliente FROM cat_equipos")
    res = cursor.fetchall()
    conn.close()
    return res

def generar_id(tipo_prefijo, fecha_str):
    conn = sqlite3.connect('erp_montacargas.db')
    cursor = conn.cursor()
    dt_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
    fecha_formateada = dt_obj.strftime("%d%m%Y")
    tabla = "trabajos" if tipo_prefijo == "tr" else ("gastos" if tipo_prefijo == "ga" else "rentas")
    cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
    count = cursor.fetchone()[0]
    conn.close()
    return f"{tipo_prefijo}_{fecha_formateada}_{count + 1:03d}"

def get_capital_inicial():
    conn = sqlite3.connect('erp_montacargas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM config WHERE clave = 'capital_inicial'")
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0.0

def set_capital_inicial(monto):
    conn = sqlite3.connect('erp_montacargas.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES ('capital_inicial', ?)", (monto,))
    conn.commit()
    conn.close()

# Encabezado con Logo y Título
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

# Botón de Respaldo Maestro Global en la barra lateral
with st.sidebar:
    st.header("🛡️ Respaldo del Sistema")
    st.write("Descarga todo tu ERP en un solo archivo de Excel organizado por pestañas:")
    
    conn = sqlite3.connect('erp_montacargas.db')
    df_t_ex = pd.read_sql_query("SELECT * FROM trabajos", conn)
    df_g_ex = pd.read_sql_query("SELECT * FROM gastos", conn)
    df_r_ex = pd.read_sql_query("SELECT * FROM rentas", conn)
    df_cli_ex = pd.read_sql_query("SELECT * FROM cat_clientes", conn)
    df_eq_ex = pd.read_sql_query("SELECT * FROM cat_equipos", conn)
    df_cat_ex = pd.read_sql_query("SELECT * FROM cat_categorias", conn)
    df_sub_ex = pd.read_sql_query("SELECT * FROM cat_subcategorias", conn)
    df_prov_ex = pd.read_sql_query("SELECT * FROM cat_proveedores", conn)
    df_cta_ex = pd.read_sql_query("SELECT * FROM cat_cuentas", conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_t_ex.to_excel(writer, sheet_name='Trabajos', index=False)
        df_g_ex.to_excel(writer, sheet_name='Gastos', index=False)
        df_r_ex.to_excel(writer, sheet_name='Rentas', index=False)
        df_cli_ex.to_excel(writer, sheet_name='Clientes', index=False)
        df_eq_ex.to_excel(writer, sheet_name='Equipos', index=False)
        df_cat_ex.to_excel(writer, sheet_name='Categorias', index=False)
        df_sub_ex.to_excel(writer, sheet_name='Subcategorias', index=False)
        df_prov_ex.to_excel(writer, sheet_name='Proveedores', index=False)
        df_cta_ex.to_excel(writer, sheet_name='Cuentas', index=False)
    
    excel_data = output.getvalue()
    
    st.download_button(
        label="📥 Descargar Respaldo Total (.xlsx)",
        data=excel_data,
        file_name=f"Respaldo_ERP_Montacargas_{datetime.today().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

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
    
    conn = sqlite3.connect('erp_montacargas.db')
    df_t = pd.read_sql_query("SELECT * FROM trabajos", conn)
    df_g = pd.read_sql_query("SELECT * FROM gastos", conn)
    conn.close()
    
    col_m1, col_m2 = st.columns(2)
    anos_disponibles = [str(datetime.now().year)]
    if not df_t.empty:
        anos_t = pd.to_datetime(df_t['fecha'], errors='coerce').dt.year.dropna().unique()
        anos_disponibles = sorted(list(set([str(y) for y in anos_t] + [str(datetime.now().year)])))
        
    anio_sel = col_m1.selectbox("Seleccionar Año", anos_disponibles, index=len(anos_disponibles)-1)
    
    meses_nombres = ["Todos", "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio", 
                     "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"]
    
    mes_actual_num = datetime.now().month
    mes_sel = col_m2.selectbox("Seleccionar Mes", meses_nombres, index=mes_actual_num)
    
    df_t_f = df_t.copy()
    df_g_f = df_g.copy()
    
    if not df_t_f.empty:
        df_t_f['dt'] = pd.to_datetime(df_t_f['fecha'], errors='coerce')
        df_t_f = df_t_f[df_t_f['dt'].dt.year == int(anio_sel)]
        if mes_sel != "Todos":
            num_mes = int(mes_sel.split(" - ")[0])
            df_t_f = df_t_f[df_t_f['dt'].dt.month == num_mes]
            
    if not df_g_f.empty:
        df_g_f['dt'] = pd.to_datetime(df_g_f['fecha'], errors='coerce')
        df_g_f = df_g_f[df_g_f['dt'].dt.year == int(anio_sel)]
        if mes_sel != "Todos":
            num_mes = int(mes_sel.split(" - ")[0])
            df_g_f = df_g_f[df_g_f['dt'].dt.month == num_mes]

    num_trabajos_mes = len(df_t_f)
    
    df_cotizados_mes = df_t_f[df_t_f['estado_financiero'].isin(['Por Cotizar', 'Cotizado']) | (df_t_f['estado_trabajo'] == 'N/A (Cotización)')]
    cotizado_mes = df_cotizados_mes['total'].sum() if not df_cotizados_mes.empty else 0.0

    df_facturados_mes = df_t_f[df_t_f['estado_financiero'].isin(['Facturado', 'Pagado']) | (df_t_f['factura'].notna() & (df_t_f['factura'] != ''))]
    facturado_mes = df_facturados_mes['total'].sum() if not df_facturados_mes.empty else 0.0
    num_facturas = df_facturados_mes.shape[0]
    
    df_pagados_mes = df_t_f[df_t_f['estado_pago'] == 'Pagado']
    cobrado_mes = df_pagados_mes['total'].sum() if not df_pagados_mes.empty else 0.0
    
    df_pendientes_cobro = df_t_f[(df_t_f['estado_pago'] != 'Pagado') & (df_t_f['estado_financiero'].isin(['Aprobado', 'Facturado']))]
    pendiente_mes = df_pendientes_cobro['total'].sum() if not df_pendientes_cobro.empty else 0.0
    
    costo_fiscal_mes = 0.0
    subtotal_ingresos_reales = 0.0
    if not df_pagados_mes.empty:
        for _, row in df_pagados_mes.iterrows():
            sub_val = float(row.get('subtotal', 0.0)) if pd.notna(row.get('subtotal')) else 0.0
            subtotal_ingresos_reales += sub_val
            if row.get('cuenta_deposito') == 'Cansino':
                costo_fiscal_mes += sub_val * 0.08
    
    subtotal_gastos_mes = df_g_f['subtotal'].sum() if not df_g_f.empty else 0.0
    gastos_totales_mes = df_g_f['total'].sum() if not df_g_f.empty else 0.0
    
    utilidad_mes = subtotal_ingresos_reales - subtotal_gastos_mes
    comp_3_mes = utilidad_mes * 0.03 if utilidad_mes > 0 else 0.0
    
    fac_angel = df_facturados_mes[df_facturados_mes['facturado_por'] == 'Angel Llanez']['total'].sum() if not df_facturados_mes.empty else 0.0
    fac_montalvo = df_facturados_mes[df_facturados_mes['facturado_por'] == 'Adolfo Montalvo']['total'].sum() if not df_facturados_mes.empty else 0.0
    
    df_todos_pagados = df_t[df_t['estado_pago'] == 'Pagado'] if not df_t.empty else pd.DataFrame()
    ing_angel_cuenta = df_todos_pagados[df_todos_pagados['cuenta_deposito'] == 'Cuenta Llanez']['subtotal'].sum() if not df_todos_pagados.empty else 0.0
    ing_montalvo_cuenta = df_todos_pagados[df_todos_pagados['cuenta_deposito'] == 'Cuenta Montalvo']['subtotal'].sum() if not df_todos_pagados.empty else 0.0
    ing_cansino = df_todos_pagados[df_todos_pagados['cuenta_deposito'] == 'Cansino']['subtotal'].sum() if not df_todos_pagados.empty else 0.0
    
    capital_inicial = get_capital_inicial()
    subtotal_hist_pagados = df_todos_pagados['subtotal'].sum() if not df_todos_pagados.empty else 0.0
    subtotal_hist_gastos = df_g['subtotal'].sum() if not df_g.empty else 0.0
    utilidad_historica_global = subtotal_hist_pagados - subtotal_hist_gastos
    capital_total_actual = capital_inicial + utilidad_historica_global
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Cotizado (Total)", f"${cotizado_mes:,.2f}")
    c2.metric("Facturado", f"${facturado_mes:,.2f}", f"{num_facturas} Facturas")
    c3.metric("Pagado (Cobrado)", f"${cobrado_mes:,.2f}")
    c4.metric("Pendiente de Cobro", f"${pendiente_mes:,.2f}")
    c5.metric("Costo Fiscal", f"${costo_fiscal_mes:,.2f}")
    
    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Capital Total Actual", f"${capital_total_actual:,.2f}", f"Inicial: ${capital_inicial:,.2f}")
    c7.metric("Gastos del Mes", f"${gastos_totales_mes:,.2f}")
    c8.metric("Utilidad Neta (Pagados)", f"${utilidad_mes:,.2f}")
    c9.metric("Compensación 3%", f"${comp_3_mes:,.2f}")
    c10.metric("Trabajos del Mes", f"{num_trabajos_mes}")
    
    st.markdown("---")
    
    st.subheader("👥 Control y Rendimiento por Socio")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Facturado por Ángel Llanez (AL)", f"${fac_angel:,.2f}")
    sc2.metric("Facturado por Adolfo Montalvo (AM)", f"${fac_montalvo:,.2f}")
    sc3.metric("Ingresos en Cuenta Cansino", f"${ing_cansino:,.2f}")

    sc4, sc5, _ = st.columns(3)
    sc4.metric("Ingresado (Cuenta Llanez)", f"${ing_angel_cuenta:,.2f}")
    sc5.metric("Ingresado (Cuenta Montalvo)", f"${ing_montalvo_cuenta:,.2f}")

    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📈 Ingresos Cobrados vs Gastos del Mes")
        df_bar = pd.DataFrame({
            'Concepto': ['Subtotal Cobrado', 'Subtotal Gastos', 'Utilidad Neta'],
            'Monto': [subtotal_ingresos_reales, subtotal_gastos_mes, utilidad_mes]
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
    
    conn = sqlite3.connect('erp_montacargas.db')
    df_t = pd.read_sql_query("SELECT * FROM trabajos", conn)
    conn.close()

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
                
                usar_f_cot = st.checkbox("¿Incluir Fecha Cotización?", value=True)
                fecha_cot = st.date_input("Fecha Cotización", value=datetime.today()) if usar_f_cot else None
                
                oc = st.text_input("O.C. (Opcional)")
                usar_f_oc = st.checkbox("¿Incluir Fecha O.C.?", value=False)
                fecha_oc = st.date_input("Fecha O.C.", value=datetime.today()) if usar_f_oc else None
            with tc4:
                factura = st.text_input("Factura (Opcional)")
                facturado_por = st.selectbox("Facturado Por", ["-- Pendiente / Sin facturar --", "Angel Llanez", "Adolfo Montalvo", "Externo"])
                subtotal = st.number_input("Subtotal ($)", min_value=0.0, step=0.01)
                iva = subtotal * 0.16
                total = subtotal + iva
                cuenta_dep = st.selectbox("Cuenta donde se depositó", lista_cuentas)
                estado_pago = st.selectbox("Estado de Pago", ["Pendiente", "Pagado", "Parcial"])
                
                usar_f_pago = st.checkbox("¿Incluir Fecha de Pago?", value=False)
                fecha_pago = st.date_input("Fecha de Pago", value=datetime.today()) if usar_f_pago else None
                
                portal = st.selectbox("Portal", ["Pendiente de Subir", "Sí", "No"])

            if st.form_submit_button("Guardar Registro en el Sistema"):
                fecha_str = str(fecha_t)
                id_gen = generar_id("tr", fecha_str)
                eq_final = "" if equipo_sel == "Sin equipo" else equipo_sel
                f_cot_str = str(fecha_cot) if fecha_cot else ""
                f_oc_str = str(fecha_oc) if fecha_oc else ""
                f_pago_str = str(fecha_pago) if fecha_pago else ""
                fac_por_final = "" if facturado_por == "-- Pendiente / Sin facturar --" else facturado_por
                cta_final = "" if cuenta_dep == "-- Sin asignar --" else cuenta_dep
                
                conn = sqlite3.connect('erp_montacargas.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trabajos (id_personalizado, fecha, cliente, equipo, modelo, serie, categoria, subcategoria, descripcion, recibo_correctivo, recibo_preventivo, estado_trabajo, estado_financiero, cotizacion, fecha_cotizacion, oc, fecha_oc, factura, facturado_por, subtotal, iva, total, cuenta_deposito, estado_pago, fecha_pago, portal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (id_gen, fecha_str, cliente, eq_final, modelo, serie, categoria, subcategoria, descripcion, recibo_corr, recibo_preventivo, estado_trabajo, estado_financiero, cotizacion, f_cot_str, oc, f_oc_str, factura, fac_por_final, subtotal, iva, total, cta_final, estado_pago, f_pago_str, portal))
                conn.commit()
                conn.close()
                st.success(f"¡Registro guardado con éxito! ID asignado: {id_gen}")
                st.rerun()

    if not df_t.empty:
        lista_ids = [str(x) for x in df_t['id_personalizado'].tolist() if x is not None and str(x) != 'nan' and str(x) != '']
        with st.expander("✏️ Editar o 🗑️ Borrar Trabajo Existente", expanded=False):
            id_a_editar = st.selectbox("Selecciona el ID del Trabajo a Editar/Borrar", lista_ids)
            registro_actual = df_t[df_t['id_personalizado'] == id_a_editar].iloc[0]
            
            with st.form("form_editar_trabajo"):
                st.write(f"Editando Registro: **{id_a_editar}**")
                
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    est_t_opts = ["Pendiente", "En Proceso", "Terminado", "Entregado", "N/A (Cotización)"]
                    val_t = registro_actual['estado_trabajo']
                    idx_t = est_t_opts.index(val_t) if val_t in est_t_opts else 0
                    nuevo_estatus_t = st.selectbox("Estado de Trabajo", est_t_opts, index=idx_t)

                    est_f_opts = ["Por Cotizar", "Cotizado", "Aprobado", "Facturado", "Pagado"]
                    val_f = registro_actual['estado_financiero']
                    idx_f = est_f_opts.index(val_f) if val_f in est_f_opts else 0
                    nuevo_estatus_f = st.selectbox("Estado Financiero", est_f_opts, index=idx_f)

                    est_p_opts = ["Pendiente", "Pagado", "Parcial"]
                    val_p = registro_actual['estado_pago']
                    idx_p = est_p_opts.index(val_p) if val_p in est_p_opts else 0
                    nuevo_estatus_p = st.selectbox("Estado de Pago", est_p_opts, index=idx_p)
                
                with ec2:
                    fac_opts = ["-- Pendiente / Sin facturar --", "Angel Llanez", "Adolfo Montalvo", "Externo"]
                    val_fac = registro_actual['facturado_por'] if pd.notna(registro_actual['facturado_por']) and registro_actual['facturado_por'] != '' else "-- Pendiente / Sin facturar --"
                    idx_fac = fac_opts.index(val_fac) if val_fac in fac_opts else 0
                    nuevo_fac_por = st.selectbox("Facturado Por", fac_opts, index=idx_fac)

                    val_factura_txt = registro_actual['factura'] if pd.notna(registro_actual['factura']) else ""
                    nueva_factura = st.text_input("Factura No.", value=val_factura_txt)

                    val_oc_txt = registro_actual['oc'] if pd.notna(registro_actual['oc']) else ""
                    nueva_oc = st.text_input("O.C.", value=val_oc_txt)
                
                with ec3:
                    val_cta = registro_actual['cuenta_deposito'] if pd.notna(registro_actual['cuenta_deposito']) and registro_actual['cuenta_deposito'] != '' else "-- Sin asignar --"
                    idx_cta = lista_cuentas.index(val_cta) if val_cta in lista_cuentas else 0
                    nueva_cuenta = st.selectbox("Cuenta donde se depositó", lista_cuentas, index=idx_cta)

                    portal_opts = ["Pendiente de Subir", "Sí", "No"]
                    val_portal = registro_actual['portal'] if pd.notna(registro_actual['portal']) else "Pendiente de Subir"
                    idx_portal = portal_opts.index(val_portal) if val_portal in portal_opts else 0
                    nuevo_portal = st.selectbox("Portal", portal_opts, index=idx_portal)

                    sub_val_ant = float(registro_actual['subtotal']) if pd.notna(registro_actual['subtotal']) else 0.0
                    nuevo_subtotal = st.number_input("Subtotal ($)", value=sub_val_ant, step=0.01)

                    val_fp_ant = registro_actual['fecha_pago'] if pd.notna(registro_actual['fecha_pago']) and registro_actual['fecha_pago'] != '' else str(datetime.today().date())
                    try:
                        dt_fp = datetime.strptime(val_fp_ant, "%Y-%m-%d").date()
                    except:
                        dt_fp = datetime.today().date()
                    
                    usar_f_pago_ed = st.checkbox("¿Actualizar / Incluir Fecha de Pago?", value=bool(val_fp_ant))
                    nueva_fecha_pago = st.date_input("Fecha de Pago", value=dt_fp) if usar_f_pago_ed else ""
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("💾 Guardar Cambios"):
                    nuevo_iva = nuevo_subtotal * 0.16
                    nuevo_total = nuevo_subtotal + nuevo_iva
                    fac_por_fin = "" if nuevo_fac_por == "-- Pendiente / Sin facturar --" else nuevo_fac_por
                    cta_fin = "" if nueva_cuenta == "-- Sin asignar --" else nueva_cuenta
                    f_pago_fin = str(nueva_fecha_pago) if nueva_fecha_pago else ""
                    
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE trabajos SET estado_trabajo = ?, estado_financiero = ?, estado_pago = ?, 
                                           facturado_por = ?, factura = ?, oc = ?, cuenta_deposito = ?, 
                                           portal = ?, subtotal = ?, iva = ?, total = ?, fecha_pago = ?
                        WHERE id_personalizado = ?
                    ''', (nuevo_estatus_t, nuevo_estatus_f, nuevo_estatus_p, fac_por_fin, nueva_factura, 
                          nueva_oc, cta_fin, nuevo_portal, nuevo_subtotal, nuevo_iva, nuevo_total, f_pago_fin, id_a_editar))
                    conn.commit()
                    conn.close()
                    st.success("¡Trabajo actualizado con éxito!")
                    st.rerun()
                    
                if col_btn2.form_submit_button("🗑️ Eliminar Trabajo"):
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM trabajos WHERE id_personalizado = ?', (id_a_editar,))
                    conn.commit()
                    conn.close()
                    st.warning("Trabajo eliminado.")
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 Historial de Trabajos")
    if not df_t.empty:
        st.dataframe(df_t, use_container_width=True)
    else:
        st.info("No hay trabajos registrados todavía.")

# ==========================================
# PESTAÑA 3: GASTOS Y TRAZABILIDAD
# ==========================================
with tab_gastos:
    st.header("💸 Gastos y Trazabilidad por Trabajo")
    
    conn = sqlite3.connect('erp_montacargas.db')
    df_g = pd.read_sql_query("SELECT * FROM gastos", conn)
    conn.close()

    provs_df = get_catalogo("cat_proveedores")
    lista_proveedores = provs_df['nombre'].tolist() if not provs_df.empty else ["Sin Proveedores"]

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
                
                conn = sqlite3.connect('erp_montacargas.db')
                t_list = pd.read_sql_query("SELECT id_personalizado, cliente, equipo FROM trabajos", conn)
                conn.close()
                trabajos_opciones = ["Ninguno"] + [f"{r['id_personalizado']} - {r['cliente']} ({r['equipo']})" for _, r in t_list.iterrows()] if not t_list.empty else ["Ninguno"]
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
                
                conn = sqlite3.connect('erp_montacargas.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gastos (id_personalizado, fecha, cliente, equipo, categoria, subcategoria, proveedor, trabajo_relacionado, descripcion, folio_ticket, metodo_pago, cuenta, subtotal, iva, total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (id_gen_g, fecha_str, cliente_g, eq_g_final, categoria_g, subcategoria_g, proveedor_g, trabajo_rel, desc_g, folio_ticket, metodo_pago, cta_g_final, sub_g, iva_g, tot_g))
                conn.commit()
                conn.close()
                st.success(f"¡Gasto registrado con éxito! ID: {id_gen_g}")
                st.rerun()

    st.markdown("---")
    st.subheader("📊 Historial de Gastos")
    if not df_g.empty:
        st.dataframe(df_g, use_container_width=True)
    else:
        st.info("No hay gastos registrados todavía.")

# ==========================================
# PESTAÑA 4: MÓDULO DE RENTAS
# ==========================================
with tab_rentas:
    st.header("🛞 Módulo de Control de Rentas")
    st.write("Administra los equipos rentados, vigencias, montos y genera cotizaciones / trabajos automáticos cuando toque el pago.")
    
    conn = sqlite3.connect('erp_montacargas.db')
    df_rentas = pd.read_sql_query("SELECT * FROM rentas", conn)
    conn.close()
    
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
                
                conn = sqlite3.connect('erp_montacargas.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO rentas (id_personalizado, cliente, equipo, fecha_inicio, fecha_fin, monto, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (id_r, cli_renta, eq_r_final, str(f_inicio), str(f_fin), monto_renta, estado_renta))
                conn.commit()
                conn.close()
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
                    subt = row['monto']
                    iva_t = subt * 0.16
                    tot_t = subt + iva_t
                    desc_trabajo = f"Renta mensual de equipo {row['equipo']} correspondiente al periodo {row['fecha_inicio']} al {row['fecha_fin']}"
                    
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO trabajos (id_personalizado, fecha, cliente, equipo, categoria, subcategoria, descripcion, estado_trabajo, estado_financiero, subtotal, iva, total, estado_pago)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (id_nuevo_trabajo, fecha_hoy_str, row['cliente'], row['equipo'], "Renta", "Renta Mensual", desc_trabajo, "Pendiente", "Por Cotizar", subt, iva_t, tot_t, "Pendiente"))
                    conn.commit()
                    conn.close()
                    st.success(f"¡Trabajo generado con éxito en Trabajos y Operaciones con ID: {id_nuevo_trabajo}!")
                
                if col_ra2.button("🗑️ Borrar Renta", key=f"del_renta_{row['id_personalizado']}"):
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM rentas WHERE id_personalizado = ?", (row['id_personalizado'],))
                    conn.commit()
                    conn.close()
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
    st.write("Agrega, edita o elimina los elementos estandarizados para mantener limpios los menús desplegables.")

    sub_cat_tab1, sub_cat_tab2, sub_cat_tab3, sub_cat_tab4, sub_cat_tab5, sub_cat_tab6 = st.tabs([
        "🏢 Clientes", 
        "🚜 Equipos", 
        "🏷️ Categorías", 
        "📂 Subcategorías", 
        "🤝 Proveedores", 
        "💳 Cuentas"
    ])

    # Carga previa segura de clientes para catálogos
    clients_df_tab = get_catalogo("cat_clientes")
    clients_for_eq = clients_df_tab['nombre'].tolist() if not clients_df_tab.empty else ["General"]

    # 1. CLIENTES
    with sub_cat_tab1:
        st.subheader("Administrar Clientes")
        with st.form("add_cli", clear_on_submit=True):
            nuevo_cli = st.text_input("Nombre del Nuevo Cliente")
            if st.form_submit_button("Agregar Cliente"):
                if nuevo_cli.strip():
                    try:
                        conn = sqlite3.connect('erp_montacargas.db')
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO cat_clientes (nombre) VALUES (?)", (nuevo_cli.strip(),))
                        conn.commit()
                        conn.close()
                        st.success("¡Cliente agregado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("El cliente ya existe.")
        
        st.markdown("---")
        if not clients_df_tab.empty:
            for _, row_c in clients_df_tab.iterrows():
                cid, cname = row_c['id'], row_c['nombre']
                with st.expander(f"Cliente: {cname}"):
                    with st.form(f"form_edit_cli_{cid}"):
                        edit_cname = st.text_input("Modificar Nombre", value=cname)
                        col_eb1, col_eb2 = st.columns(2)
                        if col_eb1.form_submit_button("💾 Guardar Cambios"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE cat_clientes SET nombre = ? WHERE id = ?", (edit_cname.strip(), cid))
                            conn.commit()
                            conn.close()
                            st.success("¡Actualizado!")
                            st.rerun()
                        if col_eb2.form_submit_button("🗑️ Borrar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM cat_clientes WHERE id = ?", (cid,))
                            conn.commit()
                            conn.close()
                            st.warning("Eliminado.")
                            st.rerun()

    # 2. EQUIPOS
    with sub_cat_tab2:
        st.subheader("Administrar Equipos")
        with st.form("add_eq", clear_on_submit=True):
            eq_eco = st.text_input("Número Económico (Ej. ECO-01)")
            eq_marca = st.text_input("Marca")
            eq_modelo = st.text_input("Modelo")
            eq_serie = st.text_input("Serie")
            eq_cliente = st.selectbox("Cliente Asociado / Propio", clients_for_eq)
            
            if st.form_submit_button("Agregar Equipo"):
                if eq_eco.strip():
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO cat_equipos (eco, marca, modelo, serie, cliente) VALUES (?, ?, ?, ?, ?)", 
                                   (eq_eco.strip(), eq_marca.strip(), eq_modelo.strip(), eq_serie.strip(), eq_cliente))
                    conn.commit()
                    conn.close()
                    st.success("¡Equipo agregado!")
                    st.rerun()
        
        st.markdown("---")
        eqs_df_tab = get_equipos_catalogo_df()
        if not eqs_df_tab.empty:
            for _, e in eqs_df_tab.iterrows():
                with st.expander(f"Eco: {e['eco']} | {e['marca']} {e['modelo']}"):
                    with st.form(f"form_edit_eq_{e['id']}"):
                        ed_eco = st.text_input("Número Económico", value=e['eco'])
                        ed_marca = st.text_input("Marca", value=e['marca'])
                        ed_modelo = st.text_input("Modelo", value=e['modelo'])
                        ed_serie = st.text_input("Serie", value=e['serie'])
                        ed_cli = st.selectbox("Cliente", clients_for_eq, index=clients_for_eq.index(e['cliente']) if e['cliente'] in clients_for_eq else 0)
                        
                        col_eq1, col_eq2 = st.columns(2)
                        if col_eq1.form_submit_button("💾 Guardar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE cat_equipos SET eco=?, marca=?, modelo=?, serie=?, cliente=? WHERE id=?", 
                                           (ed_eco.strip(), ed_marca.strip(), ed_modelo.strip(), ed_serie.strip(), ed_cli, e['id']))
                            conn.commit()
                            conn.close()
                            st.success("¡Actualizado!")
                            st.rerun()
                        if col_eq2.form_submit_button("🗑️ Borrar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM cat_equipos WHERE id = ?", (e['id'],))
                            conn.commit()
                            conn.close()
                            st.warning("Eliminado.")
                            st.rerun()

    # 3. CATEGORÍAS
    with sub_cat_tab3:
        st.subheader("Administrar Categorías")
        with st.form("add_cat", clear_on_submit=True):
            n_cat = st.text_input("Nueva Categoría")
            if st.form_submit_button("Agregar Categoría"):
                if n_cat.strip():
                    try:
                        conn = sqlite3.connect('erp_montacargas.db')
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO cat_categorias (nombre) VALUES (?)", (n_cat.strip(),))
                        conn.commit()
                        conn.close()
                        st.success("¡Categoría agregada!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe.")
        st.markdown("---")
        cats_df_tab = get_catalogo("cat_categorias")
        if not cats_df_tab.empty:
            for _, row_cat in cats_df_tab.iterrows():
                cid, cname = row_cat['id'], row_cat['nombre']
                with st.expander(f"Categoría: {cname}"):
                    with st.form(f"form_edit_cat_{cid}"):
                        ed_cname = st.text_input("Modificar", value=cname)
                        cb1, cb2 = st.columns(2)
                        if cb1.form_submit_button("💾 Guardar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE cat_categorias SET nombre=? WHERE id=?", (ed_cname.strip(), cid))
                            conn.commit()
                            conn.close()
                            st.rerun()
                        if cb2.form_submit_button("🗑️ Borrar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM cat_categorias WHERE id=?", (cid,))
                            conn.commit()
                            conn.close()
                            st.rerun()

    # 4. SUBCATEGORÍAS
    with sub_cat_tab4:
        st.subheader("Administrar Subcategorías")
        with st.form("add_subcat", clear_on_submit=True):
            n_sub = st.text_input("Nueva Subcategoría")
            if st.form_submit_button("Agregar Subcategoría"):
                if n_sub.strip():
                    try:
                        conn = sqlite3.connect('erp_montacargas.db')
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO cat_subcategorias (nombre) VALUES (?)", (n_sub.strip(),))
                        conn.commit()
                        conn.close()
                        st.success("¡Agregada!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe.")
        st.markdown("---")
        sub_df_tab = get_catalogo("cat_subcategorias")
        if not sub_df_tab.empty:
            for _, row_sub in sub_df_tab.iterrows():
                cid, cname = row_sub['id'], row_sub['nombre']
                with st.expander(f"Subcategoría: {cname}"):
                    with st.form(f"form_edit_subcat_{cid}"):
                        ed_sname = st.text_input("Modificar", value=cname)
                        sb1, sb2 = st.columns(2)
                        if sb1.form_submit_button("💾 Guardar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE cat_subcategorias SET nombre=? WHERE id=?", (ed_sname.strip(), cid))
                            conn.commit()
                            conn.close()
                            st.rerun()
                        if sb2.form_submit_button("🗑️ Borrar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM cat_subcategorias WHERE id=?", (cid,))
                            conn.commit()
                            conn.close()
                            st.rerun()

    # 5. PROVEEDORES
    with sub_cat_tab5:
        st.subheader("Administrar Proveedores")
        with st.form("add_prov", clear_on_submit=True):
            n_prov = st.text_input("Nombre del Proveedor")
            if st.form_submit_button("Agregar Proveedor"):
                if n_prov.strip():
                    try:
                        conn = sqlite3.connect('erp_montacargas.db')
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO cat_proveedores (nombre) VALUES (?)", (n_prov.strip(),))
                        conn.commit()
                        conn.close()
                        st.success("¡Agregado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe.")
        st.markdown("---")
        prov_df_tab = get_catalogo("cat_proveedores")
        if not prov_df_tab.empty:
            for _, row_p in prov_df_tab.iterrows():
                cid, cname = row_p['id'], row_p['nombre']
                with st.expander(f"Proveedor: {cname}"):
                    with st.form(f"form_edit_prov_{cid}"):
                        ed_pname = st.text_input("Modificar", value=cname)
                        pb1, pb2 = st.columns(2)
                        if pb1.form_submit_button("💾 Guardar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE cat_proveedores SET nombre=? WHERE id=?", (ed_pname.strip(), cid))
                            conn.commit()
                            conn.close()
                            st.rerun()
                        if pb2.form_submit_button("🗑️ Borrar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM cat_proveedores WHERE id=?", (cid,))
                            conn.commit()
                            conn.close()
                            st.rerun()

    # 6. CUENTAS
    with sub_cat_tab6:
        st.subheader("Administrar Cuentas / Bancos")
        with st.form("add_cta", clear_on_submit=True):
            n_cta = st.text_input("Nombre de la Cuenta o Método")
            if st.form_submit_button("Agregar Cuenta"):
                if n_cta.strip():
                    try:
                        conn = sqlite3.connect('erp_montacargas.db')
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO cat_cuentas (nombre) VALUES (?)", (n_cta.strip(),))
                        conn.commit()
                        conn.close()
                        st.success("¡Agregado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe.")
        st.markdown("---")
        cta_df_tab = get_catalogo("cat_cuentas")
        if not cta_df_tab.empty:
            for _, row_cta in cta_df_tab.iterrows():
                cid, cname = row_cta['id'], row_cta['nombre']
                with st.expander(f"Cuenta: {cname}"):
                    with st.form(f"form_edit_cta_{cid}"):
                        ed_cname = st.text_input("Modificar", value=cname)
                        cb1, cb2 = st.columns(2)
                        if cb1.form_submit_button("💾 Guardar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE cat_cuentas SET nombre=? WHERE id=?", (ed_cname.strip(), cid))
                            conn.commit()
                            conn.close()
                            st.rerun()
                        if cb2.form_submit_button("🗑️ Borrar"):
                            conn = sqlite3.connect('erp_montacargas.db')
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM cat_cuentas WHERE id=?", (cid,))
                            conn.commit()
                            conn.close()
                            st.rerun()
