import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configuración de la página web
st.set_page_config(page_title="Mi Mini-ERP - Cuentas y Equipos", layout="wide")

# Inicializar la Base de Datos SQLite local
def init_db():
    conn = sqlite3.connect('erp_equipos.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL, 
            concepto TEXT NOT NULL,
            categoria TEXT NOT NULL,
            equipo TEXT,
            cliente TEXT,
            subtotal REAL NOT NULL,
            iva REAL NOT NULL,
            monto REAL NOT NULL,
            cotizacion TEXT,
            oc TEXT,
            factura TEXT,
            estatus TEXT,
            fecha TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Título principal
st.title("🏢 Mi Mini-ERP - Control de Cuentas y Equipos")

# Sección de Resumen Superior (Tarjetas)
conn = sqlite3.connect('erp_equipos.db')
df_registros = pd.read_sql_query("SELECT * FROM registros ORDER BY fecha DESC", conn)
conn.close()

if not df_registros.empty:
    total_ingresos = df_registros[df_registros['tipo'] == 'Ingreso']['monto'].sum()
    total_egresos = df_registros[df_registros['tipo'] == 'Egreso']['monto'].sum()
else:
    total_ingresos = 0.0
    total_egresos = 0.0

utilidad = total_ingresos - total_egresos

col1, col2, col3 = st.columns(3)
col1.metric("🟢 Ingresos Totales", f"${total_ingresos:,.2f}")
col2.metric("🔴 Egresos Totales", f"${total_egresos:,.2f}")
col3.metric("🔵 Utilidad Neta", f"${utilidad:,.2f}")

st.markdown("---")

# Formulario para Registrar Nuevo Movimiento
st.subheader("📝 Registrar Nuevo Movimiento")

with st.form("form_registro", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    
    with c1:
        tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
        concepto = st.text_input("Concepto / Descripción", placeholder="Ej. Servicio de mantenimiento")
        categoria = st.text_input("Categoría", placeholder="Ej. Venta, Renta, Refacción")
        equipo = st.text_input("Equipo (Opcional)", placeholder="Ej. Equipo A, Planta")
        
    with c2:
        cliente = st.text_input("Cliente", placeholder="Nombre del cliente")
        subtotal = st.number_input("Subtotal ($)", min_value=0.0, step=0.01, format="%.2f")
        aplica_iva = st.selectbox("¿Aplica IVA (16%)?", ["Sí (Calcular 16%)", "No (IVA 0)"])
        
        # Cálculo automático de IVA en tiempo real
        iva_val = subtotal * 0.16 if aplica_iva == "Sí (Calcular 16%)" else 0.0
        total_val = subtotal + iva_val
        
        st.text(f"IVA Calculado: ${iva_val:,.2f}")
        st.text(f"Total con IVA: ${total_val:,.2f}")

    with c3:
        cotizacion = st.text_input("No. Cotización", placeholder="Ej. COT-001")
        oc = st.text_input("Orden de Compra (OC)", placeholder="Ej. OC-9876")
        factura = st.text_input("Factura", placeholder="Factura")
        estatus = st.selectbox("Estatus", ["Pendiente", "Pagado", "Facturado"])
        fecha = st.date_input("Fecha", value=datetime.today())

    enviar = st.form_submit_button("Guardar en el Sistema")

    if enviar:
        if concepto.strip() == "" or categoria.strip() == "":
            st.error("Por favor completa al menos el Concepto y la Categoría.")
        else:
            conn = sqlite3.connect('erp_equipos.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO registros (tipo, concepto, categoria, equipo, cliente, subtotal, iva, monto, cotizacion, oc, factura, estatus, fecha) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tipo, concepto, categoria, equipo, cliente, subtotal, iva_val, total_val, cotizacion, oc, factura, estatus, str(fecha)))
            conn.commit()
            conn.close()
            st.success("¡Movimiento guardado con éxito!")
            st.rerun()

st.markdown("---")

# Historial y Botón de Resguardo a Excel
col_hist, col_btn = st.columns([3, 1])
col_hist.subheader("📊 Historial de Registros")

if not df_registros.empty:
    # Botón para descargar Excel directo
    archivo_excel = "Resguardo_ERP.xlsx"
    df_registros.to_excel(archivo_excel, index=False)
    
    with open(archivo_excel, "rb") as f:
        col_btn.download_button(
            label="📥 Descargar Resguardo",
            data=f,
            file_name="Resguardo_ERP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Mostrar la tabla bonita
    st.dataframe(df_registros, use_container_width=True)
else:
    st.info("Aún no hay registros guardados. ¡Agrega el primero arriba!")