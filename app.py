from flask import Flask, render_template_string, request, redirect, url_for, send_file
import sqlite3
import pandas as pd
import os

app = Flask(__name__)

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

@app.route('/')
def index():
    conn = sqlite3.connect('erp_equipos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registros ORDER BY fecha DESC")
    registros = cursor.fetchall()
    
    cursor.execute("SELECT SUM(monto) FROM registros WHERE tipo = 'Ingreso'")
    res_ingreso = cursor.fetchone()[0]
    total_ingresos = float(res_ingreso) if res_ingreso is not None else 0.0
    
    cursor.execute("SELECT SUM(monto) FROM registros WHERE tipo = 'Egreso'")
    res_egreso = cursor.fetchone()[0]
    total_egresos = float(res_egreso) if res_egreso is not None else 0.0
    
    utilidad = total_ingresos - total_egresos
    conn.close()
    
    html = '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Mi Mini-ERP - Control Financiero</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: #eef2f5; color: #333; }
            header { background: #2c3e50; color: white; padding: 15px 40px; display: flex; justify-content: space-between; align-items: center; }
            .logo-area { display: flex; align-items: center; gap: 15px; }
            .logo-area img { height: 45px; border-radius: 4px; background: white; padding: 2px; }
            header h1 { margin: 0; font-size: 20px; }
            .container { padding: 30px 40px; max-width: 1400px; margin: auto; }
            .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px; }
            .resumen { display: flex; gap: 20px; margin-bottom: 25px; }
            .box { flex: 1; padding: 20px; border-radius: 8px; color: white; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .ingreso { background: linear-gradient(135deg, #27ae60, #2ecc71); }
            .egreso { background: linear-gradient(135deg, #c0392b, #e74c3c); }
            .utilidad { background: linear-gradient(135deg, #2980b9, #3498db); }
            .box h3 { margin: 0 0 10px 0; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; }
            .box p { margin: 0; font-size: 26px; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
            th, td { padding: 12px 10px; border-bottom: 1px solid #e1e8ed; text-align: left; }
            th { background: #f8f9fa; color: #2c3e50; font-weight: 600; }
            input, select { padding: 10px; margin: 6px 0 15px 0; width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }
            label { font-weight: 600; font-size: 13px; color: #475569; }
            button { background: #2563eb; color: white; border: none; padding: 12px 20px; cursor: pointer; border-radius: 6px; font-weight: bold; font-size: 14px; transition: background 0.2s; }
            button:hover { background: #1d4ed8; }
            .btn-excel { background: #10b981; text-decoration: none; display: inline-block; padding: 10px 20px; color: white; border-radius: 6px; font-weight: bold; font-size: 14px; }
            .btn-excel:hover { background: #059669; }
            .form-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
            .badge-ingreso { color: #16a34a; font-weight: bold; }
            .badge-egreso { color: #dc2626; font-weight: bold; }
        </style>
        <script>
            function calcularTotal() {
                let subtotal = parseFloat(document.getElementById('subtotal').value) || 0;
                let aplicaIva = document.getElementById('aplica_iva').value;
                let iva = 0;
                if (aplicaIva === 'si') {
                    iva = subtotal * 0.16;
                }
                let total = subtotal + iva;
                document.getElementById('iva_display').value = iva.toFixed(2);
                document.getElementById('monto_total').value = total.toFixed(2);
            }
        </script>
    </head>
    <body>
        <header>
            <div class="logo-area">
                <!-- Aquí se mostrará tu logo si pones logo.png en la carpeta -->
                <img src="/static/logo.png" alt="Logo Empresa" onerror="this.style.display='none'">
                <h1>Control de Cuentas y Equipos</h1>
            </div>
            <a href="/exportar" class="btn-excel">📥 Descargar Resguardo a Excel</a>
        </header>
        
        <div class="container">
            <div class="resumen">
                <div class="box ingreso">
                    <h3>Ingresos Totales</h3>
                    <p>$ {{ "%.2f"|format(total_ingresos) }}</p>
                </div>
                <div class="box egreso">
                    <h3>Egresos Totales</h3>
                    <p>$ {{ "%.2f"|format(total_egresos) }}</p>
                </div>
                <div class="box utilidad">
                    <h3>Utilidad Neta</h3>
                    <p>$ {{ "%.2f"|format(utilidad) }}</p>
                </div>
            </div>

            <div class="card">
                <h3 style="margin-top: 0; color: #1e293b; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px;">Registrar Nuevo Movimiento</h3>
                <form action="/agregar" method="POST">
                    <div class="form-grid">
                        <div>
                            <label>Tipo de Movimiento:</label>
                            <select name="tipo">
                                <option value="Ingreso">Ingreso</option>
                                <option value="Egreso">Egreso</option>
                            </select>
                            
                            <label>Concepto / Descripción:</label>
                            <input type="text" name="concepto" placeholder="Ej. Servicio de mantenimiento" required>
                            
                            <label>Categoría:</label>
                            <input type="text" name="categoria" placeholder="Ej. Venta, Renta, Refacción" required>

                            <label>Equipo:</label>
                            <input type="text" name="equipo" placeholder="Ej. Equipo A, Planta">
                        </div>
                        <div>
                            <label>Cliente:</label>
                            <input type="text" name="cliente" placeholder="Nombre del cliente">

                            <label>Subtotal ($):</label>
                            <input type="number" step="0.01" name="subtotal" id="subtotal" placeholder="0.00" oninput="calcularTotal()" required>

                            <label>¿Aplica IVA (16%):</label>
                            <select id="aplica_iva" name="aplica_iva" onchange="calcularTotal()">
                                <option value="si">Sí (Calcular 16%)</option>
                                <option value="no">No (IVA 0)</option>
                            </select>

                            <label>IVA Calculado ($):</label>
                            <input type="text" id="iva_display" readonly value="0.00" style="background: #f8f9fa;">
                        </div>
                        <div>
                            <label>Total con IVA ($):</label>
                            <input type="number" step="0.01" name="monto" id="monto_total" placeholder="0.00" readonly style="background: #f8f9fa;" required>

                            <label>No. Cotización:</label>
                            <input type="text" name="cotizacion" placeholder="Ej. COT-001">

                            <label>Orden de Compra (OC):</label>
                            <input type="text" name="oc" placeholder="Ej. OC-9876">

                            <div style="display: flex; gap: 10px;">
                                <div style="flex: 1;">
                                    <label>Factura:</label>
                                    <input type="text" name="factura" placeholder="Factura">
                                </div>
                                <div style="flex: 1;">
                                    <label>Estatus:</label>
                                    <select name="estatus">
                                        <option value="Pendiente">Pendiente</option>
                                        <option value="Pagado">Pagado</option>
                                        <option value="Facturado">Facturado</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <label>Fecha (AAAA-MM-DD):</label>
                    <input type="date" name="fecha" required style="width: 30%;">

                    <br>
                    <button type="submit" style="margin-top: 10px;">Guardar Registro</button>
                </form>
            </div>

            <div class="card">
                <h3 style="margin-top: 0; color: #1e293b; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px;">Historial de Registros</h3>
                <div style="overflow-x: auto;">
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>Tipo</th>
                            <th>Cliente</th>
                            <th>Concepto</th>
                            <th>Equipo</th>
                            <th>Subtotal</th>
                            <th>IVA</th>
                            <th>Total</th>
                            <th>Cot / OC / Fact</th>
                            <th>Estatus</th>
                            <th>Fecha</th>
                        </tr>
                        {% for r in registros %}
                        <tr>
                            <td>{{ r[0] }}</td>
                            <td><span class="{{ 'badge-ingreso' if r[1] == 'Ingreso' else 'badge-egreso' }}">{{ r[1] }}</span></td>
                            <td>{{ r[5] }}</td>
                            <td>{{ r[2] }}</td>
                            <td>{{ r[4] }}</td>
                            <td>$ {{ "%.2f"|format(r[6]) }}</td>
                            <td>$ {{ "%.2f"|format(r[7]) }}</td>
                            <td><b>$ {{ "%.2f"|format(r[8]) }}</b></td>
                            <td><small>Cot: {{ r[9] }}<br>OC: {{ r[10] }}<br>Fac: {{ r[11] }}</small></td>
                            <td><b>{{ r[12] }}</b></td>
                            <td>{{ r[13] }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, registros=registros, total_ingresos=total_ingresos, total_egresos=total_egresos, utilidad=utilidad)

@app.route('/agregar', methods=['POST'])
def agregar():
    tipo = request.form['tipo']
    concepto = request.form['concepto']
    categoria = request.form['categoria']
    equipo = request.form['equipo']
    cliente = request.form['cliente']
    subtotal_val = float(request.form['subtotal'])
    aplica_iva = request.form.get('aplica_iva')
    
    iva_val = (subtotal_val * 0.16) if aplica_iva == 'si' else 0.0
    total_val = subtotal_val + iva_val
    
    cotizacion = request.form['cotizacion']
    oc = request.form['oc']
    factura = request.form['factura']
    estatus = request.form['estatus']
    fecha = request.form['fecha']
    
    conn = sqlite3.connect('erp_equipos.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO registros (tipo, concepto, categoria, equipo, cliente, subtotal, iva, monto, cotizacion, oc, factura, estatus, fecha) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tipo, concepto, categoria, equipo, cliente, subtotal_val, iva_val, total_val, cotizacion, oc, factura, estatus, fecha))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/exportar')
def exportar():
    conn = sqlite3.connect('erp_equipos.db')
    df = pd.read_sql_query("SELECT * FROM registros", conn)
    conn.close()
    
    archivo_excel = "Resguardo_ERP.xlsx"
    df.to_excel(archivo_excel, index=False)
    
    return send_file(archivo_excel, as_attachment=True)

import os

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)