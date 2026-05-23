# Auto Solution - Gestión de Inventario

Este proyecto es una aplicación web empresarial destinada al control integral de stock, catálogo de productos, compras, márgenes de ganancia y registro de ventas de repuestos y lubricantes en el taller mecánico automotriz.

El sistema funciona de manera autónoma con su propio almacén de base de datos local y su propio control de usuarios y seguridad.

---

## Tecnologías y Lenguajes Utilizados

El software se ha construido empleando herramientas de desarrollo eficientes y modernas:

* **Backend (Servidor)**:
  * **Python 3.10+**: Lógica principal del servidor.
  * **Flask**: Framework encargado de resolver peticiones HTTP, enrutamiento, validación y gestión de sesiones.
  * **SQLite3**: Base de datos relacional para almacenar tanto la información de inventario (`base_datos/productos.db`) como el control local de cuentas de usuario (`base_datos/usuarios.db`).
* **Frontend (Interfaz de Usuario)**:
  * **HTML5**: Estructuración semántica de las vistas principales del inventario y el carrito de compras.
  * **CSS3 (Vanilla)**: Maquetación adaptativa, moderna y estilizada por componentes (tablas financieras, grids de productos, formularios de carga).
  * **JavaScript (Vanilla - ES6)**: Manipulación dinámica de tablas, registro interactivo en la zona de ventas (carrito) y peticiones AJAX asíncronas hacia el backend.

---

## Requisitos e Instalación

### Requisitos del Sistema
* **Python 3.10** o superior instalado.

### Instrucciones de Instalación
1. Navega al directorio del proyecto:
   ```bash
   cd Gestion_inventario_auto_solution/inventario
   ```

2. Crea y activa tu entorno virtual de Python:
   ```bash
   # En Windows
   python -m venv venv
   venv\Scripts\activate
   
   # En Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instala los paquetes requeridos:
   ```bash
   pip install -r requirements.txt
   ```

4. Genera o verifica las bases de datos locales ejecutando el script de inicialización (o simplemente arranca la aplicación, que creará de forma automática las bases de datos vacías y el usuario administrador por defecto):
   ```bash
   python ../generar.py
   ```

5. Inicia el servidor de Flask:
   ```bash
   python app.py
   ```
   *(La aplicación estará disponible en http://localhost:5000 o https://localhost:5000 si SSL está configurado).*

---

## Descripción de las Páginas del Sistema

El módulo de inventario organiza sus funciones de manera clara para el usuario:

| Página / Vista | Archivo de Plantilla | Descripción Funcional |
| :--- | :--- | :--- |
| **Inicio de Sesión** | [login.html](file:///C:/Users/corte/Documents/aplicaciones/Gestion_inventario_auto_solution/inventario/templates/login.html) | Pantalla de acceso seguro que autentica al personal del taller según su perfil operativo local. |
| **Catálogo e Inventario** | [tablas.html](file:///C:/Users/corte/Documents/aplicaciones/Gestion_inventario_auto_solution/inventario/templates/tablas.html) | Vista principal del inventario. Muestra tablas interactivas con la lista de repuestos, stock disponible y precios. Oculta automáticamente las columnas financieras (neto, ganancia, IVA) si el usuario tiene rol básico. |
| **Agregar Productos** | [agregar.html](file:///C:/Users/corte/Documents/aplicaciones/Gestion_inventario_auto_solution/inventario/templates/agregar.html) | Formulario de entrada rápida para dar de alta nuevos artículos en el inventario. Permite definir de forma dinámica marcas, tipos de repuestos y proveedores de contacto. |
| **Zona de Ventas** | [ventas.html](file:///C:/Users/corte/Documents/aplicaciones/Gestion_inventario_auto_solution/inventario/templates/ventas.html) | Terminal de punto de venta (POS) interactivo. Los técnicos o editores pueden buscar repuestos, agregarlos a un carrito y procesar la salida de mercancía, lo que descuenta el stock de manera automática en la base de datos. |
| **Historial de Ventas** | [historial.html](file:///C:/Users/corte/Documents/aplicaciones/Gestion_inventario_auto_solution/inventario/templates/historial.html) | Registro histórico de todas las salidas y ventas de productos realizadas desde la zona de ventas, permitiendo auditorías de mercadería. |
| **Usuarios del Sistema** | [admin_usuarios.html](file:///C:/Users/corte/Documents/aplicaciones/Gestion_inventario_auto_solution/inventario/templates/admin_usuarios.html) | Panel administrativo (exclusivo para `admin`) que gestiona de manera directa el archivo de usuarios local de inventario. |

---

## Mecanismos de Seguridad Implementados

El sistema garantiza la integridad de los datos financieros del taller mediante estrictas validaciones:

1. **Criptografía con Bcrypt**:
   * Las contraseñas se almacenan mediante hashes criptográficos irreversibles utilizando **bcrypt** con salt dinámico, protegiendo las credenciales contra ataques de diccionario o robos físicos de base de datos.
2. **Privacidad de Datos Financieros (Ocultación Estricta)**:
   * Los usuarios regulares de nivel básico (`visor` o `usuario regular`) **no tienen permitido ver columnas de costos sensibles** (precio de compra, porcentaje de utilidad, neto sin IVA, ni valor del impuesto). 
   * Esta restricción se valida y sanitiza **en el servidor (backend)** antes de enviar las respuestas JSON, previniendo que los usuarios puedan inspeccionar el código de la página o las respuestas de la consola para leer la información protegida.
3. **Control de Acceso Basado en Roles (RBAC)**:
   * **`admin`**: Acceso total al catálogo, precios, métricas financieras de compra-venta y módulo de administración de usuarios.
   * **`editor`**: Puede consultar inventario, reabastecer o crear productos y registrar ventas, pero tiene bloqueado el acceso a la sección de administración de cuentas.
   * **`usuario regular` / `visor`**: Únicamente puede visualizar la lista de productos y stock para saber si un repuesto está disponible. Tiene deshabilitado el acceso a catálogos de proveedores y tablas de marcas.
4. **Cifrado de Capa de Transporte (HTTPS/SSL)**:
   * Soporte condicional para TLS/HTTPS nativo. Si los archivos `cert.pem` y `key.pem` están presentes en la raíz de la aplicación, Flask de desarrollo iniciará de forma automática como servidor HTTPS seguro.
   * Se incluye un script para autogenerar claves de desarrollo local utilizando criptografía de Python nativa:
     ```bash
     python generar_certificados.py
     ```

```
