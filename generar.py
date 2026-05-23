import sqlite3
import os
import sys
import bcrypt

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "base_datos")
DB = os.path.join(DB_DIR, "productos.db")
DB_USUARIOS = os.path.join(DB_DIR, "usuarios.db")

def crear_base_datos():
    os.makedirs(DB_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS TiposProducto (
            id_tipo INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_tipo TEXT NOT NULL,
            descripcion TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Proveedores (
            id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            email TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Marcas (
            id_marca INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_marca TEXT NOT NULL,
            descripcion TEXT
        )
    ''')
    
    cursor.execute('''
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
    ''')
    
    cursor.execute('''
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
    ''')
    
    conn.commit()
    conn.close()
    
    conn_u = sqlite3.connect(DB_USUARIOS)
    cursor_u = conn_u.cursor()
    cursor_u.execute('''
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
    ''')
    conn_u.commit()
    conn_u.close()
    
    print("Tablas creadas correctamente")

def verificar_y_migrar_columnas():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(HistorialVentas)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'id_marca' not in columnas:
            print("Migrando: agregando columna id_marca...")
            cursor.execute('ALTER TABLE HistorialVentas ADD COLUMN id_marca INTEGER')
        
        if 'nombre_marca' not in columnas:
            print("Migrando: agregando columna nombre_marca...")
            cursor.execute('ALTER TABLE HistorialVentas ADD COLUMN nombre_marca TEXT')
        
        if 'precio_sin_descuento' not in columnas:
            print("Migrando: agregando columna precio_sin_descuento...")
            cursor.execute('ALTER TABLE HistorialVentas ADD COLUMN precio_sin_descuento DECIMAL(10,2)')
        
        if 'descuento_porcentaje' not in columnas:
            print("Migrando: agregando columna descuento_porcentaje...")
            cursor.execute('ALTER TABLE HistorialVentas ADD COLUMN descuento_porcentaje DECIMAL(5,2) DEFAULT 0')
        
        conn.commit()
        print("Migración completada")
    except Exception as e:
        print(f"Columnas ya existen o migración no necesaria: {e}")
    finally:
        conn.close()

def hashear_contrasena(contrasena):
    return bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt(10))

def insertar_usuarios_iniciales():
    conn = sqlite3.connect(DB_USUARIOS)
    cursor = conn.cursor()
    
    try:
        hash_contrasena = hashear_contrasena('admin')
        cursor.execute(
            "INSERT INTO Usuarios (usuario, contrasena, rol, activo) VALUES (?, ?, ?, 1)",
            ('admin', hash_contrasena, 'admin')
        )
        print("Usuario 'admin' (rol: admin) creado")
    except sqlite3.IntegrityError:
        print("Usuario 'admin' ya existe")
    
    conn.commit()
    conn.close()

def insertar_datos_iniciales():
    pass

def main():
    print("\nGENERADOR DE BASE DE DATOS - GESTION INVENTARIO AUTO\n")
    
    if os.path.exists(DB) or os.path.exists(DB_USUARIOS):
        print(f"Las bases de datos ya existen en: {DB_DIR}")
        respuesta = input("Deseas recrearlas? (s/n): ").lower()
        if respuesta == 's':
            if os.path.exists(DB):
                os.remove(DB)
            if os.path.exists(DB_USUARIOS):
                os.remove(DB_USUARIOS)
            print("Bases de datos anteriores eliminadas")
        else:
            print("Ejecutando migración de columnas faltantes...")
            verificar_y_migrar_columnas()
            return
    
    print(f"Ubicacion: {DB_DIR}\n")
    
    crear_base_datos()
    verificar_y_migrar_columnas()
    insertar_datos_iniciales()
    insertar_usuarios_iniciales()
    
    print("Base de datos generada correctamente")
    print("Usuario admin / admin creado")

if __name__ == "__main__":
    main()