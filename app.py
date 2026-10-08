import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
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
        CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY,
            valor REAL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def generar_id(tipo_prefijo, fecha_str):
    conn = sqlite3.connect('erp_montacargas.db')
    cursor = conn.cursor()
    dt_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
    fecha_formateada = dt_obj.strftime("%d%m%Y")
    tabla = "trabajos" if tipo_prefijo == "tr" else "gastos"
    cursor.execute(f"SELECT COUNT(*) FROM {tabla} WHERE fecha = ?", (fecha_str,))
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

tab_dash, tab_trabajos, tab_gastos, tab_config = st.tabs([
    "📊 Dashboard e Indicadores", 
    "💼 Trabajos y Operaciones", 
    "💸 Gastos y Trazabilidad", 
    "⚙️ Configuración & Capital"
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
    
    # Calcular el mes actual por defecto (ej. mes 10 -> index correspondiente)
    mes_actual_num = datetime.now().month
    indice_mes_default = mes_actual_num # porque "Todos" es el índice 0, y Enero es 1, etc.
    
    mes_sel = col_m2.selectbox("Seleccionar Mes", meses_nombres, index=indice_mes_default)
    
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
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Trabajos del Mes", f"{num_trabajos_mes}")
    c2.metric("Facturado", f"${facturado_mes:,.2f}", f"{num_facturas} Facturas")
    c3.metric("Cobrado este mes", f"${cobrado_mes:,.2f}")
    c4.metric("Pendiente (Mes)", f"${pendiente_mes:,.2f}")
    c5.metric("Costo Fiscal", f"${costo_fiscal_mes:,.2f}")
    
    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Facturado (AL)", f"${fac_angel:,.2f}")
    c7.metric("Facturado (AM)", f"${fac_montalvo:,.2f}")
    c8.metric("Gastos del Mes", f"${gastos_totales_mes:,.2f}")
    c9.metric("Utilidad (Sin IVA)", f"${utilidad_mes:,.2f}")
    c10.metric("Compensación 3%", f"${comp_3_mes:,.2f}")
    
    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📈 Ingresos vs Gastos del Mes")
        if not df_t_f.empty or not df_g_f.empty:
            df_bar = pd.DataFrame({
                'Concepto': ['Subtotal Ingresos', 'Subtotal Gastos', 'Utilidad (Sin IVA)'],
                'Monto': [subtotal_trabajos_mes, subtotal_gastos_mes, utilidad_mes]
            })
            st.bar_chart(df_bar.set_index('Concepto'))
        else:
            st.info("Sin datos para mostrar gráfica en este periodo.")
            
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

    # Registrar Nuevo Trabajo
    with st.expander("➕ Registrar Nuevo Trabajo", expanded=False):
        with st.form("form_trabajo"):
            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1:
                fecha_t = st.date_input("Fecha", value=datetime.today())
                cliente = st.text_input("Cliente")
                equipo = st.text_input("Equipo")
                modelo = st.text_input("Modelo")
                serie = st.text_input("Serie")
            with tc2:
                categoria = st.selectbox("Categoría", ["Mantenimiento", "Venta", "Renta", "Refacción", "Servicio Correctivo", "Servicio Preventivo"])
                subcategoria = st.text_input("Subcategoría")
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
                cuenta_dep = st.selectbox("Cuenta donde se depositó", ["Cuenta Llanez", "Cuenta Montalvo", "Efectivo", "Cansino"])
                estado_pago = st.selectbox("Estado de Pago", ["Pendiente", "Pagado", "Parcial"])
                portal = st.selectbox("Portal", ["Sí", "No", "Pendiente de Subir"])

            if st.form_submit_button("Guardar Trabajo en el Sistema"):
                fecha_str = str(fecha_t)
                id_gen = generar_id("tr", fecha_str)
                
                conn = sqlite3.connect('erp_montacargas.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trabajos (id_personalizado, fecha, cliente, equipo, modelo, serie, categoria, subcategoria, descripcion, recibo_correctivo, recibo_preventivo, estado_trabajo, estado_financiero, cotizacion, fecha_cotizacion, oc, fecha_oc, factura, facturado_por, subtotal, iva, total, cuenta_deposito, estado_pago, portal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (id_gen, fecha_str, cliente, equipo, modelo, serie, categoria, subcategoria, descripcion, recibo_corr, recibo_prev, estado_trabajo, estado_financiero, cotizacion, str(fecha_cot), oc, str(fecha_oc), factura, facturado_por, subtotal, iva, total, cuenta_dep, estado_pago, portal))
                conn.commit()
                conn.close()
                st.success(f"¡Trabajo registrado con éxito! ID asignado: {id_gen}")
                st.rerun()

    # Sección para Editar o Eliminar Trabajos (Ahora maneja IDs personalizados o registros anteriores)
    if not df_t.empty:
        # Filtrar solo los que tienen id_personalizado o mostrar todos
        lista_ids = [str(x) for x in df_t['id_personalizado'].tolist() if x is not None and str(x) != 'nan' and str(x) != '']
        if not lista_ids:
            # Si hay registros viejos sin id_personalizado, les asignamos uno temporalmente en pantalla para poder editarlos
            df_t['id_personalizado'] = df_t['id_personalizado'].fillna("antiguo_" + df_t.index.astype(str))
            lista_ids = df_t['id_personalizado'].tolist()

        with st.expander("✏️ Editar o 🗑️ Borrar Trabajo Existente", expanded=True):
            id_a_editar = st.selectbox("Selecciona el ID del Trabajo a Editar/Borrar", lista_ids)
            registro_actual = df_t[df_t['id_personalizado'] == id_a_editar].iloc[0]
            
            with st.form("form_editar_trabajo"):
                st.write(f"Editando Registro: **{id_a_editar}**")
                
                # Manejar índices seguros para selectbox
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
                actualizar = col_btn1.form_submit_button("💾 Guardar Cambios")
                eliminar = col_btn2.form_submit_button("🗑️ Eliminar Trabajo")
                
                if actualizar:
                    nuevo_iva = nuevo_subtotal * 0.16
                    nuevo_total = nuevo_subtotal + nuevo_iva
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    
                    # Actualizar por id_personalizado real
                    cursor.execute('''
                        UPDATE trabajos SET estado_trabajo = ?, estado_pago = ?, subtotal = ?, iva = ?, total = ?
                        WHERE id_personalizado = ?
                    ''', (nuevo_estatus_t, nuevo_estatus_p, nuevo_subtotal, nuevo_iva, nuevo_total, id_a_editar))
                    conn.commit()
                    conn.close()
                    st.success("¡Trabajo actualizado con éxito!")
                    st.rerun()
                    
                if eliminar:
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM trabajos WHERE id_personalizado = ?', (id_a_editar,))
                    conn.commit()
                    conn.close()
                    st.warning(f"Trabajo {id_a_editar} eliminado.")
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

    # Registrar Nuevo Gasto
    with st.expander("➕ Registrar Nuevo Gasto", expanded=False):
        with st.form("form_gasto"):
            gc1, gc2, gc3 = st.columns(3)
            with gc1:
                fecha_g = st.date_input("Fecha Gasto", value=datetime.today())
                cliente_g = st.text_input("Cliente Relacionado")
                equipo_g = st.text_input("Equipo Relacionado")
                categoria_g = st.text_input("Categoría de Gasto")
            with gc2:
                subcategoria_g = st.text_input("Subcategoría")
                proveedor_g = st.text_input("Proveedor")
                
                conn = sqlite3.connect('erp_montacargas.db')
                t_list = pd.read_sql_query("SELECT id_personalizado, cliente, equipo FROM trabajos", conn)
                conn.close()
                trabajos_opciones = ["Ninguno"] + [f"{r['id_personalizado']} - {r['cliente']} ({r['equipo']})" for _, r in t_list.iterrows()] if not t_list.empty else ["Ninguno"]
                trabajo_rel = st.selectbox("Trabajo Relacionado (Trazabilidad)", trabajos_opciones)
            with gc3:
                folio_ticket = st.text_input("Folio de Ticket o Factura")
                metodo_pago = st.selectbox("Método de Pago", ["Transferencia", "Efectivo", "Tarjeta"])
                cuenta_g = st.selectbox("Cuenta Gasto", ["Cuenta Llanez", "Cuenta Montalvo", "Efectivo"])
                sub_g = st.number_input("Subtotal Gasto ($)", min_value=0.0, step=0.01)
                iva_g = sub_g * 0.16
                tot_g = sub_g + iva_g

            desc_g = st.text_area("Descripción / Detalle del Gasto")
            
            if st.form_submit_button("Guardar Gasto"):
                fecha_str = str(fecha_g)
                id_gen_g = generar_id("ga", fecha_str)
                
                conn = sqlite3.connect('erp_montacargas.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO gastos (id_personalizado, fecha, cliente, equipo, categoria, subcategoria, proveedor, trabajo_relacionado, descripcion, folio_ticket, metodo_pago, cuenta, subtotal, iva, total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (id_gen_g, fecha_str, cliente_g, equipo_g, categoria_g, subcategoria_g, proveedor_g, trabajo_rel, desc_g, folio_ticket, metodo_pago, cuenta_g, sub_g, iva_g, tot_g))
                conn.commit()
                conn.close()
                st.success(f"¡Gasto registrado con éxito! ID asignado: {id_gen_g}")
                st.rerun()

    # Sección para Editar o Eliminar Gastos
    if not df_g.empty:
        lista_ids_g = [str(x) for x in df_g['id_personalizado'].tolist() if x is not None and str(x) != 'nan' and str(x) != '']
        if not lista_ids_g:
            df_g['id_personalizado'] = df_g['id_personalizado'].fillna("antiguo_" + df_g.index.astype(str))
            lista_ids_g = df_g['id_personalizado'].tolist()

        with st.expander("✏️ Editar o 🗑️ Borrar Gasto Existente", expanded=False):
            id_g_editar = st.selectbox("Selecciona el ID del Gasto a Editar/Borrar", lista_ids_g)
            gasto_actual = df_g[df_g['id_personalizado'] == id_g_editar].iloc[0]
            
            with st.form("form_editar_gasto"):
                st.write(f"Editando Gasto: **{id_g_editar}**")
                sub_g_ant = float(gasto_actual['subtotal']) if pd.notna(gasto_actual['subtotal']) else 0.0
                nuevo_sub_g = st.number_input("Subtotal Gasto ($)", value=sub_g_ant, step=0.01)
                
                col_g_btn1, col_g_btn2 = st.columns(2)
                actualizar_g = col_g_btn1.form_submit_button("💾 Guardar Cambios Gasto")
                eliminar_g = col_g_btn2.form_submit_button("🗑️ Eliminar Gasto")
                
                if actualizar_g:
                    nuevo_iva_g = nuevo_sub_g * 0.16
                    nuevo_total_g = nuevo_sub_g + nuevo_iva_g
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE gastos SET subtotal = ?, iva = ?, total = ?
                        WHERE id_personalizado = ?
                    ''', (nuevo_sub_g, nuevo_iva_g, nuevo_total_g, id_g_editar))
                    conn.commit()
                    conn.close()
                    st.success("¡Gasto actualizado con éxito!")
                    st.rerun()
                    
                if eliminar_g:
                    conn = sqlite3.connect('erp_montacargas.db')
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM gastos WHERE id_personalizado = ?', (id_g_editar,))
                    conn.commit()
                    conn.close()
                    st.warning(f"Gasto {id_g_editar} eliminado.")
                    st.rerun()

    st.markdown("---")
    st.subheader("📊 Historial de Gastos")
    if not df_g.empty:
        st.dataframe(df_g, use_container_width=True)
    else:
        st.info("No hay gastos registrados todavía.")

# ==========================================
# PESTAÑA 4: CONFIGURACIÓN
# ==========================================
with tab_config:
    st.header("⚙️ Configuración del Sistema")
    capital_actual = get_capital_inicial()
    
    new_cap = st.number_input("Establecer Capital Inicial del ERP ($)", value=capital_actual, step=1000.0)
    if st.button("Actualizar Capital Inicial"):
        set_capital_inicial(new_cap)
        st.success("¡Capital inicial actualizado correctamente!")
        st.rerun()
