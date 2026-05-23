# Cambios Implementados - Base de Datos Separada de Usuarios y Productos Localizada

## Resumen
Se ha modificado la aplicación de Gestión de Inventario para utilizar dos bases de datos completamente separadas localizadas en la carpeta `base_datos/` dentro de la carpeta raíz del proyecto, eliminando la dependencia del directorio compartido:
- `base_datos/productos.db`: Contiene únicamente la información del inventario, stock, proveedores, marcas y ventas.
- `base_datos/usuarios.db`: Almacena la autenticación y control de acceso del personal de inventario.

## Cambios Realizados en `app.py`

### 1. Configuración de Rutas de Base de Datos
```python
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "base_datos")
DB = os.path.join(DB_DIR, "productos.db")
DB_USUARIOS = os.path.join(DB_DIR, "usuarios.db")
```
* Las rutas ahora apuntan a la subcarpeta `base_datos/` dentro del proyecto.

### 2. Auto-inicialización de Base de Datos
Se incorporó la función `ensure_db_files()` que se ejecuta automáticamente al iniciar la aplicación:
```python
def ensure_db_files():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    ...
```
* Esta función crea la carpeta `base_datos/` y los archivos `.db` correspondientes si no existen, inicializa las tablas del esquema y crea la cuenta por defecto `admin` con contraseña `admin` (con hash seguro bcrypt).

### 3. Funciones de Consulta
Las funciones de conexión y ejecución reciben el parámetro opcional `db_name` para direccionar las consultas a la base de datos correcta (`productos` por defecto o `usuarios` si se especifica):
* **Login**: Valida contra `DB_USUARIOS`.
* **Módulo de Usuarios**: Operaciones CRUD sobre `DB_USUARIOS`.
* **Catálogo y Ventas**: Operaciones sobre `DB`.

## Estructura de Bases de Datos

### `productos.db` (Inventario)
* Tabla: `Productos`
* Tabla: `Proveedores`
* Tabla: `TiposProducto`
* Tabla: `Marcas`
* Tabla: `HistorialVentas`

### `usuarios.db` (Autenticación)
* Tabla: `Usuarios`
  * `id_usuario`
  * `usuario`
  * `contrasena` (bcrypt)
  * `rol`
  * `email`
  * `activo`
  * `fecha_creacion`
  * `fecha_ultima_sesion`

## Verificación

1. Ejecutar el script `python ../generar.py` o iniciar la aplicación con `python app.py`.
2. Verificar que se cree la carpeta `base_datos/` con los archivos `productos.db` y `usuarios.db` correspondientes.
3. Iniciar sesión usando las credenciales de administración locales: `admin` / `admin`.
