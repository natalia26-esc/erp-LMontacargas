import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

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
    cursor.execute(f"SELECT id, nombre FROM {tabla} ORDER BY nombre ASC")
    res = cursor.fetchall()
    conn.close()
    return res if res else []

def get_equipos_catalogo():
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
    facturado_mes = df_t_f['total'].sum() if not df_t_f.empty else 0.0
    num_facturas = df_t_f[df_t_f['factura'].notna() & (df_t_f['factura'] != '')].shape[0] if not df_t_f.empty else 0
    
    cobrado_mes = df_t_f[df_t_f['estado_pago'] == 'Pagado']['total'].sum() if not df_t_f.empty else 0.0
    pendiente_mes = df_t_f[df_t_f['estado_pago'] != 'Pagado']['total'].sum() if not df_t_f.empty else 0.0
    costo_fiscal_mes = df_t_f['costo_fiscal'].sum() if not df_t_f.empty else 0.0
    
    subtotal_trabajos_mes = df_t_f['subtotal'].sum() if not df_t_f.empty else 0.0
    subtotal_gastos_mes = df_g_f['subtotal'].sum() if not df_g_f.empty else 0.0
    gastos_totales_mes = df_g_f['total'].sum() if not df_g_f.empty else 0.0
    
    utilidad_mes = subtotal_trabajos_mes - subtotal_gastos_mes
    comp_3_mes = utilidad_mes * 0.03
    
    fac_angel = df_t_f[df_t_f['facturado_por'] == 'Angel Llanez']['total'].sum() if not df_t_f.empty else 0.0
    fac_montalvo = df_t_f[df_t_f['facturado_por'] == 'Adolfo Montalvo']['total'].sum() if not df_t_f.empty else 0.0
    
    capital_inicial = get_capital_inicial()
    total_cobrado_historico = df_t[df_t['estado_pago'] == 'Pagado']['total'].sum() if not df_t.empty else 0.0
    total_gastos_historico = df_g['total'].sum() if not df_g.empty else 0.0
    capital_total_actual = capital_inicial + total_cobrado_historico - total_gastos_historico
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Trabajos del Mes", f"{num_trabajos_mes}")
    c2.metric("Facturado", f"${facturado_mes:,.2f}", f"{num_facturas} Facturas")
    c3.metric("Cobrado este mes", f"${cobrado_mes:,.2f}")
    c4.metric("Pendiente (Mes)", f"${pendiente_mes:,.2f}")
    c5.metric("Costo Fiscal", f"${costo_fiscal_mes:,.2f}")
    
    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Capital Total Actual", f"${capital_total_actual:,.2f}", f"Inicial: ${capital_inicial:,.2f}")
    c7.metric("Facturado (AM)", f"${fac_montalvo:,.2f}")
    c8.metric("Gastos del Mes", f"${gastos_totales_mes:,.2f}")
    c9.metric("Utilidad (Sin IVA)", f"${utilidad_mes:,.2f}")
    c10.metric("Compensación 3%", f"${comp_3_mes:,.2f}")
    
    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📈 Ingresos vs Gastos del Mes")
        df_bar = pd.DataFrame({
            'Concepto': ['Subtotal Ingresos', 'Subtotal Gastos', 'Utilidad (Sin IVA)'],
            'Monto': [subtotal_trabajos_mes, subtotal_gastos_mes, utilidad_mes]
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
    
    if not df_t.empty:
        archivo_t = "Resguardo_Trabajos.xlsx"
        df_t.to_excel(archivo_t, index=False)
        with open(archivo_t, "rb") as f:
            st.download_button("📥 Descargar Resguardo de Trabajos a Excel", f, file_name="Trabajos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    clientes_db = get_catalogo("cat_clientes")
    lista_clientes = [c[1] for c in clientes_db] if clientes_db else ["Sin Clientes"]
    
    cats_db = get_catalogo("cat_categorias")
    lista_categorias = [ct[1] for ct in cats_db] if cats_db else ["General"]
    
    subcats_db = get_catalogo("cat_subcategorias")
    lista_subcategorias = [sb[1] for sb in subcats_db] if subcats_db else ["General"]
    
    cuentas_db = get_catalogo("cat_cuentas")
    lista_cuentas = [cx[1] for cx in cuentas_db] if cuentas_db else ["Efectivo"]
    
    equipos_db = get_equipos_catalogo()
    lista_equipos_strs = ["Sin equipo"] + ([f"Eco: {e[1]} | {e[2]} {e[3]} (Cliente: {e[5]})" for e in equipos_db] if equipos_db else [])

    with st.expander("➕ Registrar Nuevo Trabajo", expanded=False):
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
                descripcion = st.text_area("Descripción del Trabajo")
                recibo_corr = st.text_input("Recibo Correctivo")
                recibo_prev = st.text_input("Recibo Preventivo")
            with tc3:
                estado_trabajo = st.selectbox("Estado de Trabajo", ["Pendiente", "En Proceso", "Terminado", "Entregado"])
                estado_financiero = st.selectbox("Estado Financiero", ["Por Cotizar", "Cotizado", "Aprobado", "Facturado", "Pagado"])
                cotizacion = st.text_input("Cotización")
                fecha_cot = st.date_input("Fecha Cotización", value=datetime.today())
                oc = st.text_input("O.C.")
                fecha_oc = st.date_input("Fecha O.C.", value=datetime.today())
            with tc4:
                factura = st.text_input("Factura")
                facturado_por = st.selectbox("Facturado Por", ["Angel Llanez", "Adolfo Montalvo", "Externo"])
                subtotal = st.number_input("Subtotal ($)", min_value=0.0, step=0.01)
                iva = subtotal * 0.16
                total = subtotal + iva
                cuenta_dep = st.selectbox("Cuenta donde se depositó", lista_cuentas)
                estado_pago = st.selectbox("Estado de Pago", ["Pendiente", "Pagado", "Parcial"])
                portal = st.selectbox("Portal", ["Sí", "No", "Pendiente de Subir"])

            if st.form_submit_button("Guardar Trabajo en el Sistema"):
                fecha_str = str(fecha_t)
                id_gen = generar_id("tr", fecha_str)
                eq_final = "" if equipo_sel == "Sin equipo" else equipo_sel
                
                conn = sqlite3.connect('erp_montacargas.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trabajos (id_personalizado, fecha, cliente, equipo, modelo, serie, categoria, subcategoria, descripcion, recibo_correctivo, recibo_preventivo, estado_trabajo, estado_financiero, cotizacion, fecha_cotizacion, oc, fecha_oc, factura, facturado_por, subtotal, iva, total, cuenta_deposito, estado_pago, portal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (id_gen, fecha_str, cliente, eq_final, modelo, serie, categoria, subcategoria, descripcion, recibo_corr, recibo_prev, estado_trabajo, estado_financiero, cotizacion, str(fecha_cot), oc, str(fecha_oc), factura, facturado_por, subtotal, iva, total, cuenta_dep, estado_pago, portal))
                conn.commit()
                conn.close()
                st.success(f"¡Trabajo registrado con éxito! ID asignado: {id_gen}")
                st.rerun()

    if not df_t.empty:
        lista_ids = [str(x) for x in df_t['id_personalizado'].tolist() if x is not None and str(x) != 'nan' and str(x) != '']
        with st.expander("✏️ Editar o 🗑️ Borrar Trabajo Existente", expanded=False):
            id_a_editar = st.selectbox("Selecciona el ID del Trabajo a Editar/Borrar", lista_ids)
            registro_actual = df_t[df_t['id_personalizado'] == id_a_editar].iloc[0]
            
            with st.form("form_editar_trabajo"):
                st.write(f"Editando Registro: **{id_a_editar}**")
                estados_t_opts = ["Pendiente", "En Proceso", "Terminado", "Entregado"]
                val_t = registro_actual['estado_trabajo']
                idx_t = estados_t_opts.index(val_t) if val_t in estados_t_opts else 0
                
                estados_p_opts = ["Pendiente", "Pagado", "Parcial"]
                val_p = registro_actual['estado_pago']
                idx_p = estados_p_opts.index(val_p) if val_p in estados_p_opts else 0

                nuevo_estatus_t = st.selectbox("Estado de Trabajo", estados_t_opts, index=idx_t)
                nuevo_estatus_p = st.selectbox("Estado de Pago", estados_p_opts, index=idx_p)
                sub_val_ant = float(registro_actual['subtotal']) if pd.notna(registro_actual['subtotal']) else 0.0
                nuevo_subtotal = st.number_input("Subtotal ($)", value=sub_val_ant, step=0.01)
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("💾 Guardar Cambios"):
                    nuevo_iva = nuevo_subtotal * 0.16
                    nuevo_total = nuevo_subtotal + nuevo_iva
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE trabajos SET estado_trabajo = ?, estado_pago = ?, subtotal = ?, iva = ?, total = ? WHERE id_personalizado = ?', 
                                   (nuevo_estatus_t, nuevo_estatus_p, nuevo_subtotal, nuevo_iva, nuevo_total, id_a_editar))
                    conn.commit()
                    conn.close()
                    st.success("¡Trabajo actualizado!")
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
    
    if not df_g.empty:
        archivo_g = "Resguardo_Gastos.xlsx"
        df_g.to_excel(archivo_g, index=False)
        with open(archivo_g, "rb") as f:
            st.download_button("📥 Descargar Resguardo de Gastos a Excel", f, file_name="Gastos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    provs_db = get_catalogo("cat_proveedores")
    lista_proveedores = [pv[1] for pv in provs_db] if provs_db else ["Sin Proveedores"]

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
                
                conn = sqlite3.connect('erp_montacargas.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gastos (id_personalizado, fecha, cliente, equipo, categoria, subcategoria, proveedor, trabajo_relacionado, descripcion, folio_ticket, metodo_pago, cuenta, subtotal, iva, total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (id_gen_g, fecha_str, cliente_g, eq_g_final, categoria_g, subcategoria_g, proveedor_g, trabajo_rel, desc_g, folio_ticket, metodo_pago, cuenta_g, sub_g, iva_g, tot_g))
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
        clients = get_catalogo("cat_clientes")
        for cid, cname in clients:
            with st.expander(f"Cliente: {cname}"):
                with st.form(f"form_edit_cli_{cid}"):
                    edit_cname = st.text_input("Modificar Nombre", value=cname)
                    col_eb1, col_eb2 = st.columns(2)
                    if col_eb1.form_submit_button("💾 Guardar"):
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
            eq_cliente = st.selectbox("Cliente Asociado / Propio", [c[1] for c in clients] if clients else ["General"])
            
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
        eqs = get_equipos_catalogo()
        for e in eqs:
            with st.expander(f"Eco: {e[1]} | {e[2]} {e[3]}"):
                with st.form(f"form_edit_eq_{e[0]}"):
                    ed_eco = st.text_input("Número Económico", value=e[1])
                    ed_marca = st.text_input("Marca", value=e[2])
                    ed_modelo = st.text_input("Modelo", value=e[3])
                    ed_serie = st.text_input("Serie", value=e[4])
                    ed_cli = st.selectbox("Cliente", [c[1] for c in clients] if clients else ["General"], index=[c[1] for c in clients].index(e[5]) if e[5] in [c[1] for c in clients] else 0)
                    
                    col_eq1, col_eq2 = st.columns(2)
                    if col_eq1.form_submit_button("💾 Guardar"):
                        conn = sqlite3.connect('erp_montacargas.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE cat_equipos SET eco=?, marca=?, modelo=?, serie=?, cliente=? WHERE id=?", 
                                       (ed_eco.strip(), ed_marca.strip(), ed_modelo.strip(), ed_serie.strip(), ed_cli, e[0]))
                        conn.commit()
                        conn.close()
                        st.success("¡Actualizado!")
                        st.rerun()
                    if col_eq2.form_submit_button("🗑️ Borrar"):
                        conn = sqlite3.connect('erp_montacargas.db')
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM cat_equipos WHERE id = ?", (e[0],))
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
        cats = get_catalogo("cat_categorias")
        for cid, cname in cats:
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
        subcats = get_catalogo("cat_subcategorias")
        for cid, cname in subcats:
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
        provs = get_catalogo("cat_proveedores")
        for cid, cname in provs:
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
        ctas = get_catalogo("cat_cuentas")
        for cid, cname in ctas:
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
