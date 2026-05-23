
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, session
from functools import wraps
import sqlite3
import random
import os
import sys


if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
import ssl
import socket
import bcrypt
from datetime import datetime, timedelta
from datetime import timezone as _dt_timezone

def obtener_ip_local():
    """Obtiene la dirección IP local de la máquina"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_cambiar_en_produccion'

app.config['SESSION_COOKIE_NAME'] = 'inventario_session'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "base_datos")
DB = os.path.join(DB_DIR, "productos.db")
DB_USUARIOS = os.path.join(DB_DIR, "usuarios.db")


def ensure_db_files():
    """Garantiza que el directorio base_datos y las bases de datos existan con sus tablas básicas y usuario admin"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_USUARIOS)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Usuarios (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            rol TEXT NOT NULL,
            email TEXT,
            activo INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_ultima_sesion TIMESTAMP
        )
        """
    )
    conn.commit()

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Usuarios")
    count = cursor.fetchone()[0]
    if count == 0:
        salt = bcrypt.gensalt(rounds=10)
        contrasena_hash = bcrypt.hashpw('admin'.encode('utf-8'), salt)
        cursor.execute(
            "INSERT INTO Usuarios (usuario, contrasena, rol, activo) VALUES (?, ?, ?, 1)",
            ('admin', contrasena_hash, 'admin')
        )
        conn.commit()
    conn.close()

    conn_p = sqlite3.connect(DB)
    cursor_p = conn_p.cursor()

    cursor_p.execute(
        """
        CREATE TABLE IF NOT EXISTS TiposProducto (
            id_tipo INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_tipo TEXT NOT NULL,
            descripcion TEXT
        )
        """
    )
    cursor_p.execute(
        """
        CREATE TABLE IF NOT EXISTS Proveedores (
            id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            email TEXT
        )
        """
    )
    cursor_p.execute(
        """
        CREATE TABLE IF NOT EXISTS Marcas (
            id_marca INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_marca TEXT NOT NULL,
            descripcion TEXT
        )
        """
    )
    cursor_p.execute(
        """
        CREATE TABLE IF NOT EXISTS Productos (
            id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_barra TEXT,
            nombre_producto TEXT NOT NULL,
            id_marca INTEGER,
            descripcion TEXT,
            id_tipo INTEGER,
            id_proveedor INTEGER,
            precio_compra DECIMAL(10,2),
            porcentaje_ganancia DECIMAL(5,2),
            precio_neto DECIMAL(10,2),
            iva DECIMAL(10,2),
            precio_venta DECIMAL(10,2),
            cantidad INTEGER
        )
        """
    )
    cursor_p.execute(
        """
        CREATE TABLE IF NOT EXISTS HistorialVentas (
            id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER NOT NULL,
            nombre_producto TEXT NOT NULL,
            id_marca INTEGER,
            nombre_marca TEXT,
            cantidad_vendida INTEGER NOT NULL,
            precio_sin_descuento DECIMAL(10,2) NOT NULL,
            descuento_porcentaje DECIMAL(5,2) DEFAULT 0,
            precio_unitario DECIMAL(10,2) NOT NULL,
            total_venta DECIMAL(10,2) NOT NULL,
            usuario_venta TEXT NOT NULL,
            fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(id_producto) REFERENCES Productos(id_producto),
            FOREIGN KEY(id_marca) REFERENCES Marcas(id_marca)
        )
        """
    )
    conn_p.commit()
    conn_p.close()


ensure_db_files()


def login_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        

        ultima_actividad = session.get('ultima_actividad')
        if ultima_actividad:
            ultima_actividad = datetime.fromisoformat(ultima_actividad)
            tiempo_inactividad = datetime.now() - ultima_actividad
            

            if tiempo_inactividad > timedelta(hours=2):
                session.clear()
                return redirect(url_for('login', timeout=1))
        

        session['ultima_actividad'] = datetime.now().isoformat()
        return f(*args, **kwargs)
    return decorated_function


def admin_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        

        ultima_actividad = session.get('ultima_actividad')
        if ultima_actividad:
            ultima_actividad = datetime.fromisoformat(ultima_actividad)
            tiempo_inactividad = datetime.now() - ultima_actividad
            
            if tiempo_inactividad > timedelta(hours=2):
                session.clear()
                return redirect(url_for('login', timeout=1))
        

        session['ultima_actividad'] = datetime.now().isoformat()
        
        if session.get('rol') != 'admin':
            return jsonify({'error': 'Acceso denegado. Solo administradores.'}), 403
        return f(*args, **kwargs)
    return decorated_function


def editor_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        

        ultima_actividad = session.get('ultima_actividad')
        if ultima_actividad:
            ultima_actividad = datetime.fromisoformat(ultima_actividad)
            tiempo_inactividad = datetime.now() - ultima_actividad
            
            if tiempo_inactividad > timedelta(hours=2):
                session.clear()
                return redirect(url_for('login', timeout=1))
        

        session['ultima_actividad'] = datetime.now().isoformat()
        
        if session.get('rol') not in ['admin', 'editor']:
            return jsonify({'error': 'Acceso denegado. Se requiere rol editor o superior.'}), 403
        return f(*args, **kwargs)
    return decorated_function


def verificar_contrasena(contrasena, hash_almacenado):
    """Verifica una contraseña contra su hash bcrypt"""
    try:
        return bcrypt.checkpw(contrasena.encode('utf-8'), hash_almacenado)
    except:
        return False


@app.route('/logo.png')
def logo_static():
    return send_from_directory(os.path.dirname(__file__), 'logo.png')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login con BD"""
    timeout = request.args.get('timeout')
    error = None
    
    if timeout:
        error = 'Tu sesión ha expirado por inactividad. Por favor, inicia sesión nuevamente.'
    
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        

        try:
            rows = query("SELECT id_usuario, usuario, contrasena, rol, activo FROM Usuarios WHERE usuario = ?", (usuario,), db_name='usuarios')
            
            if rows and rows[0]['activo']:
                usuario_db = rows[0]
                hash_almacenado = usuario_db['contrasena']
                

                if verificar_contrasena(contrasena, hash_almacenado):

                    execute("UPDATE Usuarios SET fecha_ultima_sesion = CURRENT_TIMESTAMP WHERE id_usuario = ?", (usuario_db['id_usuario'],), db_name='usuarios')
                    

                    session.permanent = True
                    session['id_usuario'] = usuario_db['id_usuario']
                    session['usuario'] = usuario_db['usuario']
                    session['rol'] = usuario_db['rol']
                    session['ultima_actividad'] = datetime.now().isoformat()
                    return redirect(url_for('index'))
            
            return render_template('login.html', error='Usuario o contraseña incorrectos')
        except Exception as e:
            print('Error en login:', e)
            return render_template('login.html', error='Error en la autenticación')
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    return redirect(url_for('login'))



@app.route('/generar_codigo')
@login_requerido
def generar_codigo():
    """Genera un codigo de barras unico con formato: id_tipo-numero_aleatorio"""
    id_tipo = request.args.get('id_tipo', '')
    if not id_tipo:
        return jsonify({'error': 'id_tipo requerido'}), 400
    
    while True:
        numero_aleatorio = str(random.randint(10000000, 99999999))
        codigo = f"{id_tipo}-{numero_aleatorio}"
        existe = query("SELECT 1 FROM Productos WHERE codigo_barra = ?", (codigo,))
        if not existe:
            break
    return jsonify({'codigo': codigo})

def query(sql, params=(), db_name='productos'):
    """Consultar base de datos - productos por defecto, usuarios si se especifica"""
    db_path = DB_USUARIOS if db_name == 'usuarios' else DB
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def execute(sql, params=(), db_name='productos'):
    """Ejecutar comando en base de datos - productos por defecto, usuarios si se especifica"""
    db_path = DB_USUARIOS if db_name == 'usuarios' else DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()


@app.route("/")
@login_requerido
def index():
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 20


    busqueda = request.args.get('busqueda', '')
    busqueda_desc = request.args.get('busqueda_desc', '')
    filtro_tipo = request.args.get('tipo', '')
    filtro_proveedor = request.args.get('proveedor', '')
    filtro_marca = request.args.get('marca', '')
    filtro_stock = request.args.get('stock', '')


    sql_base = "FROM Productos p "
    condiciones = []
    params = []

    if busqueda:
        condiciones.append("(p.codigo_barra LIKE ? OR p.nombre_producto LIKE ?)")
        params.extend([f"%{busqueda}%", f"%{busqueda}%"])
    
    if busqueda_desc:
        condiciones.append("p.descripcion LIKE ?")
        params.append(f"%{busqueda_desc}%")

    if filtro_tipo:
        condiciones.append("p.id_tipo = ?")
        params.append(filtro_tipo)

    if filtro_proveedor:
        condiciones.append("p.id_proveedor = ?")
        params.append(filtro_proveedor)

    if filtro_marca:
        condiciones.append("p.id_marca = ?")
        params.append(filtro_marca)

    if filtro_stock:
        if filtro_stock == 'sin-stock':
            condiciones.append("p.cantidad = 0")
        elif filtro_stock == 'poco-stock':
            condiciones.append("p.cantidad BETWEEN 1 AND 8")
        elif filtro_stock == 'normal':
            condiciones.append("p.cantidad > 8")

    sql_where = ""
    if condiciones:
        sql_where = "WHERE " + " AND ".join(condiciones)


    total_sql = "SELECT COUNT(*) AS total " + sql_base + sql_where
    total_result = query(total_sql, tuple(params))
    total_productos = total_result[0]['total'] if total_result else 0
    

    offset = (pagina - 1) * por_pagina
    total_paginas = (total_productos + por_pagina - 1) // por_pagina
    

    productos_sql = "SELECT * " + sql_base + sql_where + " LIMIT ? OFFSET ?"
    params.extend([por_pagina, offset])
    productos = query(productos_sql, tuple(params))
    
    proveedores = query("SELECT * FROM Proveedores")
    tipos = query("SELECT * FROM TiposProducto")
    marcas = query("SELECT * FROM Marcas")
    

    total_costo_result = query("SELECT COALESCE(SUM(precio_compra * cantidad), 0) AS total_costo FROM Productos")
    total_precio_costo = float(total_costo_result[0]['total_costo']) if total_costo_result else 0

    return render_template(
        "tablas.html",
        productos=productos,
        proveedores=proveedores,
        tipos=tipos,
        marcas=marcas,
        pagina_actual=pagina,
        total_paginas=total_paginas,
        total_productos=total_productos,
        total_precio_costo=total_precio_costo,
        filtros=request.args 
    )



@app.route('/agregar', methods=['GET', 'POST'])
@editor_requerido
def agregar():
    if request.method == 'GET':
        tabla = request.args.get('tabla', 'productos')
        exito = request.args.get('exito') == '1'
        proveedores = query("SELECT * FROM Proveedores")
        tipos = query("SELECT * FROM TiposProducto")
        marcas = query("SELECT * FROM Marcas")
        return render_template('agregar.html', tabla=tabla, proveedores=proveedores, tipos=tipos, marcas=marcas, exito=exito)


    form = request.form
    try:

        if 'nombre_producto' in form:
            execute("""
                INSERT INTO Productos (
                    codigo_barra, nombre_producto, descripcion,
                    id_tipo, id_proveedor, id_marca, precio_compra, porcentaje_ganancia,
                    precio_neto, iva, precio_venta, cantidad
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                form.get('codigo_barra'),
                form.get('nombre_producto'),
                form.get('descripcion'),
                form.get('id_tipo'),
                form.get('id_proveedor'),
                form.get('id_marca'),
                form.get('precio_compra') or 0,
                form.get('porcentaje_ganancia') or 0,
                form.get('precio_neto') or 0,
                form.get('iva') or 0,
                form.get('precio_venta') or 0,
                form.get('cantidad') or 0
            ))
            return redirect(url_for('agregar', tabla='productos', exito=1))


        if 'nombre' in form and 'telefono' in form:
            execute("INSERT INTO Proveedores (nombre, telefono, email) VALUES (?,?,?)", (
                form.get('nombre'), form.get('telefono'), form.get('email')
            ))
            return redirect(url_for('agregar', tabla='proveedores', exito=1))


        if 'nombre_tipo' in form:
            execute("INSERT INTO TiposProducto (nombre_tipo, descripcion) VALUES (?,?)", (
                form.get('nombre_tipo'), form.get('descripcion')
            ))
            return redirect(url_for('agregar', tabla='tipos', exito=1))
        

        if 'nombre_marca' in form:
            execute("INSERT INTO Marcas (nombre_marca, descripcion) VALUES (?,?)", (
                form.get('nombre_marca'), form.get('descripcion')
            ))
            return redirect(url_for('agregar', tabla='marcas', exito=1))

    except Exception as e:
        print('Error al insertar:', e)
        return jsonify({'status':'error', 'mensaje': str(e)})

    return redirect(url_for('agregar'))



@app.route('/ventas')
@login_requerido
def ventas():

    return render_template('ventas.html')


@app.route('/buscar_producto', methods=['POST'])
@login_requerido
def buscar_producto():
    data = request.get_json() or {}
    codigo = data.get('codigo')
    if not codigo:
        return jsonify({'error':'codigo requerido'}), 400
    rows = query('SELECT * FROM Productos WHERE codigo_barra = ? LIMIT 1', (codigo,))
    if not rows:
        return jsonify({'error':'no encontrado'}), 404
    p = rows[0]
    

    nombre_marca = None
    if p['id_marca']:
        marca_rows = query('SELECT nombre_marca FROM Marcas WHERE id_marca = ?', (p['id_marca'],))
        nombre_marca = marca_rows[0]['nombre_marca'] if marca_rows else None
    
    return jsonify({
        'id': p['id_producto'],
        'nombre': p['nombre_producto'],
        'precio': float(p['precio_venta']) if p['precio_venta'] is not None else 0,
        'stock': int(p['cantidad']) if p['cantidad'] is not None else 0,
        'id_marca': p['id_marca'],
        'nombre_marca': nombre_marca
    })


@app.route('/buscar_sugerencias', methods=['POST'])
@login_requerido
def buscar_sugerencias():
    data = request.get_json() or {}
    q = (data.get('query') or '').strip()
    if not q:
        return jsonify([]), 200
    like = q + '%'
    rows = query('SELECT * FROM Productos WHERE codigo_barra LIKE ? ORDER BY codigo_barra LIMIT 10', (like,))
    results = []
    for p in rows:
        nombre_marca = None
        if p['id_marca']:
            marca_rows = query('SELECT nombre_marca FROM Marcas WHERE id_marca = ?', (p['id_marca'],))
            nombre_marca = marca_rows[0]['nombre_marca'] if marca_rows else None
        results.append({
            'id': p['id_producto'],
            'codigo': p['codigo_barra'],
            'nombre': p['nombre_producto'],
            'precio': float(p['precio_venta']) if p['precio_venta'] is not None else 0,
            'stock': int(p['cantidad']) if p['cantidad'] is not None else 0,
            'id_marca': p['id_marca'],
            'nombre_marca': nombre_marca
        })
    return jsonify(results), 200


@app.route('/vender', methods=['POST'])
@login_requerido
def vender():
    data = request.get_json() or {}
    items = data.get('items', [])
    print(f"DEBUG: Items recibidos: {items}")
    if not items:
        return jsonify({'error':'items vacios'}), 400
    updated = []
    try:

        for it in items:
            pid = it.get('id')
            qty = int(it.get('qty', 0))

            try:
                pid_int = int(pid)
            except Exception:
                pid_int = None
            if not pid_int or pid_int <= 0:

                continue
            rows = query('SELECT cantidad FROM Productos WHERE id_producto = ?', (pid_int,))
            if not rows:
                return jsonify({'error':'producto no existe', 'id': pid}), 400
            disponible = int(rows[0]['cantidad'])
            if disponible < qty:
                return jsonify({'error':'stock insuficiente', 'id': pid, 'disponible': disponible}), 400




        venta_timestamp = datetime.now().astimezone().isoformat(timespec='seconds')
        for it in items:
            pid = it.get('id')
            qty = int(it.get('qty', 0))
            precio_sin_descuento = float(it.get('precioSinDescuento', 0))
            precio_unitario = float(it.get('precio', 0))
            descuento_porcentaje = float(it.get('descuento', 0))
            id_marca = it.get('id_marca')
            nombre_marca = it.get('nombre_marca')
            
            print(f"DEBUG - Item recibido: id={pid}, qty={qty}, precioSinDesc={precio_sin_descuento}, descuento={descuento_porcentaje}")
            

            try:
                pid_int = int(pid)
            except Exception:
                pid_int = None

            if pid_int and pid_int > 0:
                prod_rows = query('SELECT nombre_producto FROM Productos WHERE id_producto = ?', (pid_int,))
                nombre_producto = prod_rows[0]['nombre_producto'] if prod_rows else (it.get('nombre') or 'Producto')

                execute('UPDATE Productos SET cantidad = cantidad - ? WHERE id_producto = ?', (qty, pid_int))

                rows = query('SELECT cantidad FROM Productos WHERE id_producto = ?', (pid_int,))
                updated.append({'id': pid_int, 'stock': int(rows[0]['cantidad'])})
                id_para_insert = pid_int
            else:

                nombre_producto = it.get('nombre') or 'Taller'
                id_para_insert = 0


            total_venta = qty * precio_unitario

            venta_local = it.get('Local') or it.get('local')
            venta_metodo_pago = (
                it.get('metodo_Pago') or it.get('metodo_pago') or it.get('metodoPago')
                or data.get('metodo_Pago') or data.get('metodo_pago') or data.get('metodoPago')
            )
            venta_tipo_recibo = (
                it.get('tipo_recibo') or it.get('tipoRecibo')
                or data.get('tipo_recibo') or data.get('tipoRecibo')
            )
            venta_n_boleta_factura = (
                it.get('n_boleta_factura') or it.get('nBoletaFactura')
                or data.get('n_boleta_factura') or data.get('nBoletaFactura')
            )
            execute('''
                INSERT INTO HistorialVentas 
                (id_producto, nombre_producto, id_marca, nombre_marca, cantidad_vendida, precio_sin_descuento, descuento_porcentaje, precio_unitario, total_venta, Local, metodo_Pago, tipo_recibo, n_boleta_factura, usuario_venta, fecha_venta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id_para_insert, nombre_producto, id_marca, nombre_marca, qty, precio_sin_descuento, descuento_porcentaje, precio_unitario, total_venta, venta_local, venta_metodo_pago, venta_tipo_recibo, venta_n_boleta_factura, session['usuario'], venta_timestamp))

        return jsonify({'message':'Venta realizada', 'updated': updated})
    except Exception as e:
        print('Error en venta:', e)
        return jsonify({'error': str(e)}), 500


@app.route("/actualizar_producto", methods=["POST"])
@editor_requerido
def actualizar_producto():
    data = request.get_json()
    try:
        execute("""
            UPDATE Productos SET
                codigo_barra=?, nombre_producto=?, descripcion=?,
                id_tipo=?, id_proveedor=?, id_marca=?, precio_compra=?, porcentaje_ganancia=?,
                precio_neto=?, iva=?, precio_venta=?, cantidad=?
            WHERE id_producto=?
        """, (
            data["codigo_barra"],
            data["nombre_producto"],
            data["descripcion"],
            data["id_tipo"],
            data["id_proveedor"],
            data["id_marca"],
            data["precio_compra"],
            data["porcentaje_ganancia"],
            data["precio_neto"],
            data["iva"],
            data["precio_venta"],
            data["cantidad"],
            data["id_producto"]
        ))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error al actualizar producto:", e)
        return jsonify({"status": "error", "mensaje": str(e)})


@app.route("/actualizar_proveedor", methods=["POST"])
@editor_requerido
def actualizar_proveedor():
    data = request.get_json()
    try:
        execute("""
            UPDATE Proveedores SET nombre=?, telefono=?, email=?
            WHERE id_proveedor=?
        """, (
            data["nombre"],
            data["telefono"],
            data["email"],
            data["id_proveedor"]
        ))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error al actualizar proveedor:", e)
        return jsonify({"status": "error", "mensaje": str(e)})


@app.route("/actualizar_tipo", methods=["POST"])
@editor_requerido
def actualizar_tipo():
    data = request.get_json()
    try:
        execute("""
            UPDATE TiposProducto SET nombre_tipo=?, descripcion=?
            WHERE id_tipo=?
        """, (
            data["nombre_tipo"],
            data["descripcion"],
            data["id_tipo"]
        ))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error al actualizar tipo:", e)
        return jsonify({"status": "error", "mensaje": str(e)})


@app.route("/eliminar_producto", methods=["POST"])
@editor_requerido
def eliminar_producto():
    data = request.get_json()
    try:
        execute("DELETE FROM Productos WHERE id_producto = ?", (data["id_producto"],))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error al eliminar producto:", e)
        return jsonify({"status": "error", "mensaje": str(e)})


@app.route("/eliminar_proveedor", methods=["POST"])
@editor_requerido
def eliminar_proveedor():
    data = request.get_json()
    try:
        usados = query("SELECT COUNT(*) AS cnt FROM Productos WHERE id_proveedor = ?", (data["id_proveedor"],))
        if usados and usados[0]["cnt"] > 0:
            return jsonify({"status": "error", "mensaje": "No se puede eliminar: el proveedor esta asignado a productos."}), 400

        execute("DELETE FROM Proveedores WHERE id_proveedor = ?", (data["id_proveedor"],))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error al eliminar proveedor:", e)
        return jsonify({"status": "error", "mensaje": str(e)})


@app.route("/eliminar_tipo", methods=["POST"])
@editor_requerido
def eliminar_tipo():
    data = request.get_json()
    try:
        usados = query("SELECT COUNT(*) AS cnt FROM Productos WHERE id_tipo = ?", (data["id_tipo"],))
        if usados and usados[0]["cnt"] > 0:
            return jsonify({"status": "error", "mensaje": "No se puede eliminar: el tipo de producto esta asignado a productos."}), 400

        execute("DELETE FROM TiposProducto WHERE id_tipo = ?", (data["id_tipo"],))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error al eliminar tipo:", e)
        return jsonify({"status": "error", "mensaje": str(e)})


@app.route("/actualizar_marca", methods=["POST"])
@editor_requerido
def actualizar_marca():
    data = request.get_json()
    try:
        execute("""
            UPDATE Marcas SET nombre_marca=?, descripcion=?
            WHERE id_marca=?
        """, (
            data["nombre_marca"],
            data["descripcion"],
            data["id_marca"]
        ))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error al actualizar marca:", e)
        return jsonify({"status": "error", "mensaje": str(e)})


@app.route("/eliminar_marca", methods=["POST"])
@editor_requerido
def eliminar_marca():
    data = request.get_json()
    try:
        usados = query("SELECT COUNT(*) AS cnt FROM Productos WHERE id_marca = ?", (data["id_marca"],))
        if usados and usados[0]["cnt"] > 0:
            return jsonify({"status": "error", "mensaje": "No se puede eliminar: la marca esta asignada a productos."}), 400

        execute("DELETE FROM Marcas WHERE id_marca = ?", (data["id_marca"],))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("Error al eliminar marca:", e)
        return jsonify({"status": "error", "mensaje": str(e)})


@app.route('/admin/usuarios', methods=['GET', 'POST'])
@admin_requerido
def admin_usuarios():
    """Página de administración de usuarios"""
    if request.method == 'POST':
        accion = request.form.get('accion')
        

        if accion == 'crear':
            usuario = request.form.get('usuario')
            contrasena = request.form.get('contrasena')
            rol = request.form.get('rol')
            email = request.form.get('email')
            
            if not usuario or not contrasena or not rol:
                return redirect(url_for('admin_usuarios', error='Faltan datos requeridos'))
            
            try:
                salt = bcrypt.gensalt(rounds=10)
                contrasena_hash = bcrypt.hashpw(contrasena.encode('utf-8'), salt)
                execute("""
                    INSERT INTO Usuarios (usuario, contrasena, rol, email, activo)
                    VALUES (?, ?, ?, ?, 1)
                """, (usuario, contrasena_hash, rol, email), db_name='usuarios')
                return redirect(url_for('admin_usuarios', exito='Usuario creado correctamente'))
            except sqlite3.IntegrityError:
                return redirect(url_for('admin_usuarios', error='El usuario ya existe'))
            except Exception as e:
                print('Error al crear usuario:', e)
                return redirect(url_for('admin_usuarios', error='Error al crear usuario'))
        

        elif accion == 'editar':
            id_usuario = request.form.get('id_usuario')
            usuario = request.form.get('usuario')
            rol = request.form.get('rol')
            email = request.form.get('email')
            contrasena_nueva = request.form.get('contrasena_nueva')
            
            try:
                if contrasena_nueva:
                    salt = bcrypt.gensalt(rounds=10)
                    contrasena_hash = bcrypt.hashpw(contrasena_nueva.encode('utf-8'), salt)
                    execute("""
                        UPDATE Usuarios SET usuario=?, rol=?, email=?, contrasena=?
                        WHERE id_usuario=?
                    """, (usuario, rol, email, contrasena_hash, id_usuario), db_name='usuarios')
                else:
                    execute("""
                        UPDATE Usuarios SET usuario=?, rol=?, email=?
                        WHERE id_usuario=?
                    """, (usuario, rol, email, id_usuario), db_name='usuarios')
                return redirect(url_for('admin_usuarios', exito='Usuario actualizado correctamente'))
            except Exception as e:
                print('Error al actualizar usuario:', e)
                return redirect(url_for('admin_usuarios', error='Error al actualizar usuario'))
        

        elif accion == 'eliminar':
            id_usuario = request.form.get('id_usuario')
            

            if int(id_usuario) == session.get('id_usuario'):
                return redirect(url_for('admin_usuarios', error='No puedes eliminar tu propia cuenta'))
            
            try:
                execute("DELETE FROM Usuarios WHERE id_usuario = ?", (id_usuario,), db_name='usuarios')
                return redirect(url_for('admin_usuarios', exito='Usuario eliminado correctamente'))
            except Exception as e:
                print('Error al eliminar usuario:', e)
                return redirect(url_for('admin_usuarios', error='Error al eliminar usuario'))
        

        elif accion == 'cambiar_estado':
            id_usuario = request.form.get('id_usuario')
            
            if int(id_usuario) == session.get('id_usuario'):
                return redirect(url_for('admin_usuarios', error='No puedes desactivar tu propia cuenta'))
            
            try:
                usuarios = query("SELECT activo FROM Usuarios WHERE id_usuario = ?", (id_usuario,), db_name='usuarios')
                nuevo_estado = 0 if usuarios[0]['activo'] else 1
                execute("UPDATE Usuarios SET activo = ? WHERE id_usuario = ?", (nuevo_estado, id_usuario), db_name='usuarios')
                return redirect(url_for('admin_usuarios', exito='Estado del usuario actualizado'))
            except Exception as e:
                print('Error al cambiar estado:', e)
                return redirect(url_for('admin_usuarios', error='Error al cambiar estado'))
    

    error = request.args.get('error')
    exito = request.args.get('exito')
    usuarios = query("SELECT id_usuario, usuario, rol, email, activo, fecha_creacion, fecha_ultima_sesion FROM Usuarios ORDER BY fecha_creacion DESC", db_name='usuarios')
    
    return render_template('admin_usuarios.html', usuarios=usuarios, error=error, exito=exito)

@app.route('/admin/borrar_historial_ventas', methods=['POST'])
@admin_requerido
def borrar_historial_ventas():
    """Elimina todos los registros de la tabla HistorialVentas - Solo admin"""
    try:
        execute("DELETE FROM HistorialVentas")
        return jsonify({'success': True, 'mensaje': 'Todos los registros del historial de ventas han sido eliminados correctamente'})
    except Exception as e:
        print('Error al borrar historial de ventas:', e)
        return jsonify({'success': False, 'error': 'Error al eliminar el historial de ventas'}), 500

@app.route('/verificar_codigo_barra/<codigo>')
@login_requerido
def verificar_codigo_barra(codigo):
    """Verifica si un código de barras ya existe en la base de datos."""
    try:
        rows = query("SELECT 1 FROM Productos WHERE codigo_barra = ?", (codigo,))
        return jsonify({'existe': bool(rows)})
    except Exception as e:
        print(f"Error al verificar código de barras: {e}")
        return jsonify({'error': 'Error en el servidor'}), 500


@app.route('/historial')
@login_requerido
def historial():
    """Página de historial de ventas"""
    ventas = query('SELECT * FROM HistorialVentas ORDER BY fecha_venta DESC LIMIT 100')
    import json

    ventas_list = []
    for v in ventas:
        d = dict(v)
        if d.get('fecha_venta') is not None:
            d['fecha_venta'] = str(d['fecha_venta']).replace(' ', 'T')
        ventas_list.append(d)
    ventas_json = json.dumps(ventas_list, default=str)
    return render_template('historial.html', ventas=ventas, ventas_json=ventas_json)

@app.route('/api/historial')
@login_requerido
def api_historial():
    """API para obtener historial por rango de fechas y tipo"""
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')
    tipo = request.args.get('tipo', 'ventas_taller_negocio')
    ver = request.args.get('ver', 'transacciones')
    periodo = request.args.get('periodo', '')
    
    import datetime
    

    condiciones = []
    params = []
    
    if desde and hasta:
        condiciones.append("substr(fecha_venta, 1, 10) >= ? AND substr(fecha_venta, 1, 10) <= ?")
        params.extend([desde, hasta])
    

    if tipo == 'ventas_negocio':
        condiciones.append("LOWER(Local) = 'negocio'")
    elif tipo == 'ventas_taller':
        condiciones.append("LOWER(Local) = 'taller'")
    
    where_sql = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    
    query_sql = f'''
        SELECT * FROM HistorialVentas 
        {where_sql}
        ORDER BY fecha_venta DESC
    '''
    
    if params:
        ventas = query(query_sql, tuple(params))
    else:
        ventas = query(query_sql)
    

    ventas_list = []
    for v in ventas:
        fecha = v['fecha_venta']
        if fecha is not None:
            fecha_iso = str(fecha).replace(' ', 'T')
        else:
            fecha_iso = None
        ventas_list.append({
            'id_venta': v['id_venta'],
            'id_producto': v['id_producto'],
            'nombre_producto': v['nombre_producto'],
            'id_marca': v['id_marca'],
            'nombre_marca': v['nombre_marca'],
            'cantidad_vendida': v['cantidad_vendida'],
            'precio_sin_descuento': float(v['precio_sin_descuento']) if v['precio_sin_descuento'] else 0.0,
            'descuento_porcentaje': float(v['descuento_porcentaje']) if v['descuento_porcentaje'] else 0.0,
            'precio_unitario': float(v['precio_unitario']),
            'total_venta': float(v['total_venta']),
            'Local': v['Local'],
            'metodo_Pago': v['metodo_Pago'],
            'tipo_recibo': v['tipo_recibo'],
            'n_boleta_factura': v['n_boleta_factura'],
            'usuario_venta': v['usuario_venta'],
            'fecha_venta': fecha_iso
        })
    

    if ver == 'semanas':

        if periodo and '-' in periodo:
            partes = periodo.split('-')
            if len(partes) == 2 and periodo[5:7].isdigit():

                try:
                    año_mes = int(partes[0])
                    mes = int(partes[1])

                    ventas_filtradas = []
                    for venta in ventas_list:
                        if venta['fecha_venta']:
                            fecha = venta['fecha_venta'][:10]
                            try:
                                dt = datetime.datetime.strptime(fecha, '%Y-%m-%d')

                                if dt.year == año_mes and dt.month == mes:
                                    ventas_filtradas.append(venta)
                            except:
                                pass
                    ventas_list = ventas_filtradas
                except:
                    pass
            elif 'W' in periodo.upper():

                try:

                    partes_semana = periodo.replace('-W', '-w').split('-w')
                    año_w = int(partes_semana[0])
                    semana = int(partes_semana[1])
                except:
                    año_w = None
                    semana = None
                
                if año_w and semana:
                    ventas_filtradas = []
                    for venta in ventas_list:
                        if venta['fecha_venta']:
                            fecha = venta['fecha_venta'][:10]
                            try:
                                dt = datetime.datetime.strptime(fecha, '%Y-%m-%d')
                                año_iso, semana_iso, _ = dt.isocalendar()
                                if año_iso == año_w and semana_iso == semana:
                                    ventas_filtradas.append(venta)
                            except:
                                pass
                    ventas_list = ventas_filtradas
        


        if periodo and ('W' in periodo.upper() or periodo[5:7].isdigit()):

            transacciones = {}
            for venta in ventas_list:
                fechaKey = venta['fecha_venta']
                if not transacciones.get(fechaKey):
                    transacciones[fechaKey] = {
                        'fecha': fechaKey,
                        'negocio': [],
                        'taller': [],
                        'metodo_Pago': venta.get('metodo_Pago'),
                        'n_boleta_factura': venta.get('n_boleta_factura')
                    }
                tipo_venta = 'taller' if (venta['Local'] and venta['Local'].lower() == 'taller') else 'negocio'
                transacciones[fechaKey][tipo_venta].append(venta)
            
            transacciones_list = sorted(transacciones.values(), key=lambda x: x['fecha'], reverse=True)
            return jsonify({'transacciones': transacciones_list, 'ventas': ventas_list})
        
        semanas = {}
        
        for venta in ventas_list:
            if venta['fecha_venta']:
                fecha = venta['fecha_venta'][:10]
                try:
                    dt = datetime.datetime.strptime(fecha, '%Y-%m-%d')
                    año_iso, semana_iso, _ = dt.isocalendar()
                    clave = f"{año_iso}-W{semana_iso:02d}"
                    

                    fecha_dt = dt
                    dia_semana = fecha_dt.weekday()
                    fecha_lunes = fecha_dt - datetime.timedelta(days=dia_semana)
                    fecha_domingo = fecha_lunes + datetime.timedelta(days=6)
                    rango_fechas = f"{fecha_lunes.strftime('%d/%m')} - {fecha_domingo.strftime('%d/%m')}"
                    


                    primer_dia_mes = datetime.datetime(dt.year, dt.month, 1)
                    dia_primer = primer_dia_mes.weekday()

                    if dia_primer <= 3:
                        primer_lunes = primer_dia_mes - datetime.timedelta(days=dia_primer)
                    else:
                        primer_lunes = primer_dia_mes + datetime.timedelta(days=7 - dia_primer)
                    

                    if fecha_dt >= primer_lunes:
                        dias_diff = (fecha_dt - primer_lunes).days
                        semana_del_mes = (dias_diff // 7) + 1
                    else:
                        semana_del_mes = 1
                    

                    semana_display = semana_del_mes
                    
                    if clave not in semanas:
                        semanas[clave] = {
                            'periodo': clave,
                            'semana': semana_display,
                            'año': año_iso,
                            'rango': rango_fechas,
                            'negocio': 0,
                            'taller': 0,
                            'total': 0,
                            'ventas': []
                        }
                    
                    tipo_venta = 'taller' if (venta['Local'] and venta['Local'].lower() == 'taller') else 'negocio'
                    semanas[clave][tipo_venta] += venta['total_venta']
                    semanas[clave]['total'] += venta['total_venta']
                    semanas[clave]['ventas'].append(venta)
                except:
                    pass
        
        semanas_list = sorted(semanas.values(), key=lambda x: x['periodo'], reverse=True)
        return jsonify({'semanas': semanas_list})
    

    if ver == 'meses':
        meses = {}
        meses_nombres = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        for venta in ventas_list:
            if venta['fecha_venta']:
                fecha = venta['fecha_venta'][:10]
                try:
                    dt = datetime.datetime.strptime(fecha, '%Y-%m-%d')
                    año = dt.year
                    mes = dt.month
                    clave = f"{año}-{mes:02d}"
                    
                    if clave not in meses:
                        meses[clave] = {
                            'periodo': clave,
                            'nombre': meses_nombres[mes-1],
                            'año': año,
                            'mes': mes,
                            'negocio': 0,
                            'taller': 0,
                            'total': 0,
                            'ventas': []
                        }
                    
                    tipo_venta = 'taller' if (venta['Local'] and venta['Local'].lower() == 'taller') else 'negocio'
                    meses[clave][tipo_venta] += venta['total_venta']
                    meses[clave]['total'] += venta['total_venta']
                    meses[clave]['ventas'].append(venta)
                except:
                    pass
        
        meses_list = sorted(meses.values(), key=lambda x: (x['año'], x['mes']), reverse=True)
        return jsonify({'meses': meses_list})
    

    transacciones = {}
    for venta in ventas_list:
        fechaKey = venta['fecha_venta']
        if not transacciones.get(fechaKey):
            transacciones[fechaKey] = {
                'fecha': fechaKey,
                'negocio': [],
                'taller': [],
                'metodo_Pago': venta.get('metodo_Pago'),
                'n_boleta_factura': venta.get('n_boleta_factura')
            }
        tipo_venta = 'taller' if (venta['Local'] and venta['Local'].lower() == 'taller') else 'negocio'
        transacciones[fechaKey][tipo_venta].append(venta)
    
    transacciones_list = sorted(transacciones.values(), key=lambda x: x['fecha'], reverse=True)
    
    return jsonify({'ventas': ventas_list, 'transacciones': transacciones_list})


if __name__ == "__main__":

    ssl_context = None

    cert_file = os.path.join(os.path.dirname(__file__), "cert.pem")
    key_file = os.path.join(os.path.dirname(__file__), "key.pem")
    ip_local = obtener_ip_local()
    
    print("\n" + "="*70)
    print("🚀 APLICACIÓN INICIADA - GESTION DE INVENTARIO")
    print("="*70)
    print(f"✓ IP Local: {ip_local}")
    print(f"✓ Puerto: 5000")
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"\n🔒 HTTPS HABILITADO - Certificados SSL detectados")
        print(f"\n📱 Acceso desde este dispositivo:")
        print(f"   https://localhost:5000")
        print(f"\n🌐 Acceso desde otros dispositivos:")
        print(f"   https://{ip_local}:5000")
        print(f"\n⚠️  NOTA: Los navegadores pueden mostrar advertencia de certificado")
        print(f"      (Es normal, es un certificado autofirmado)")
        
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, key_file)
        print("="*70 + "\n")
        app.run(host="0.0.0.0", port=5000, ssl_context=ssl_context)
    else:
        print(f"\n📱 Acceso desde este dispositivo:")
        print(f"   http://localhost:5000")
        print(f"\n🌐 Acceso desde otros dispositivos:")
        print(f"   http://{ip_local}:5000")
        print("\n⚠️  Certificados SSL no encontrados.")
        print(f"   Buscado en: {cert_file}")
        print(f"   Ejecuta primero: python ../generar_certificados.py")
        print("   Iniciando en HTTP sin HTTPS...\n")
        print("="*70 + "\n")
        app.run(host="0.0.0.0", port=5000)

