# Conector local de Supercías para la app de escritorio de Claude

Permite que Claude consulte la Superintendencia de Compañías **desde su PC**, sin abrir una terminal:
la app de escritorio arranca este servidor y Claude lo usa como una herramienta más
(`consultar_supercias`).

## Instalar (una sola vez por computador)
1. Tener Python 3.10 o superior y esta carpeta del repositorio en el PC.
2. Doble clic en `adapters/mcp/instalar_supercias.bat`.
   Instala dependencias, registra el servidor en `claude_desktop_config.json` (guarda copia `.bak`)
   y comprueba que arranca.
3. Cerrar Claude por completo (icono de la bandeja → Salir) y abrirlo de nuevo.
4. En Ajustes → Desarrollador debe aparecer `supercias-census` en ejecución.

## Usar
- «Consulta en Supercías el RUC 0990000001001» o «¿quién es el representante legal de X?».
- «Acuerdo de confidencialidad para X»: el agente consulta, arma el YAML del cliente y genera el Word.

## Notas
- Funciona mientras la app de escritorio esté abierta en ese PC. En tareas que corren en la nube,
  la herramienta solo está disponible si la tarea está vinculada a ese computador.
- Si se mueve la carpeta del repositorio, repetir el paso 2.
- Desinstalar: borrar la entrada `supercias-census` de `claude_desktop_config.json`.
- Alternativa manual (Ajustes → Desarrollador → Editar configuración):
  ```json
  {"mcpServers": {"supercias-census": {"command": "python",
    "args": ["C:\\ruta\\a\\mi-agente-analisis\\adapters\\mcp\\supercias_server.py"]}}}
  ```

## Salidas por proxies propios (opcional)
Para consultar desde un servidor fuera de Ecuador, o repartir la carga entre varias IP fijas:
1. Crear `privado/proxies.txt` (ignorado por Git), un proxy por línea:
   ```
   # salidas Census (IP fijas de Ecuador)
   http://usuario:clave@203.0.113.10:3128
   http://usuario:clave@203.0.113.11:3128
   ```
   O, en un servidor, la variable de entorno `SUPERCIAS_PROXIES` (separados por coma).
2. Probar: `python -m core.cli salidas` (abre la página de búsqueda por cada salida, sin consultar compañías).

Funcionamiento: cada consulta usa una sola salida de principio a fin (la sesión del portal va atada a su
cookie); las consultas se reparten por turnos; si una salida falla por red, la consulta se repite por la
siguiente y la caída queda apartada 5 minutos. La pausa entre peticiones (0,4 s) se mantiene en cada salida.
Las credenciales nunca se muestran en mensajes ni se guardan en el YAML del cliente.
Sin `proxies.txt` ni variable, todo sigue por la conexión directa como antes.
