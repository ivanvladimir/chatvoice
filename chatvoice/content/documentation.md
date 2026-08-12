---
title: Documentación básica
active_page: documentation
active_menu: documentation
---

# Guía de Creación de Scripts de Conversación

Esta guía detalla cómo escribir scripts para _chatvoice_.

## 1. Estructura de Archivos y Directorios

El intérprete espera una estructura de proyecto específica. El punto de entrada siempre es un archivo `main.yaml`, pero los elementos complementarios (plantillas, prompts, plugins) se cargan desde subdirectorios.

```text
mi_proyecto/
├── main.yaml                 # Script principal (Punto de entrada)
├── recursos/                 # (Opcional) Carpeta para textos largos
│   ├── plantillas.yaml       # Diccionario de plantillas de respuesta
│   └── prompts.yaml          # Diccionario de prompts para el LLM
├── plugins/                  # (Opcional) Scripts de Python restringidos
│   └── utils.py              # Funciones personalizadas para usar con 'exec'
└── sub_conversacion.yaml     # (Opcional) Otros archivos de flujo para 'solve'
```

## 2. Estructura del archivo YAML (`main.yaml`)

El archivo YAML principal se divide en secciones clave que el intérprete carga al inicializarse:

```yaml
# Variables iniciales inyectadas en el contexto (Slots)
slots:
  idioma: "es"
  intentos: 0

# Configuración general del flujo
settings:
  _name_user: "USUARIO"

# Lista de archivos externos donde se definen las plantillas (busca en la carpeta 'resources/')
templates:
  - plantillas.yaml

# Lista de archivos externos donde se definen los prompts del LLM
prompts:
  - prompts.yaml

# Archivos de Python inyectados en el contexto de ejecución segura
plugins:
  - utils.py

# Estrategias: Flujos alternativos que no rompen la conversación actual
strategies:
  manejo_errores:
    - say "No entendí eso."
    - set intentos + 1

# Sub-conversaciones: Flujos que reemplazan el actual y permiten devolver valores
conversations:
  auth_flow: sub_conversacion.yaml

# El script en sí: Lista de líneas de comandos ejecutadas de arriba a abajo
script:
  - say "¡Hola! ¿Cómo te llamas?"
  - listen nombre
  - say "Encantado de conocerte, {nombre}."

# Opcional: se ejecuta UNA VEZ, en segundo plano, cuando la sesión termina
# (el usuario cierra la conexión). No es parte del flujo normal del script;
# ver la sección "Limpieza y análisis en segundo plano" más abajo.
cleanup:
  - llm_extract:
      system: analizar_conversacion
      user: "Analiza toda la conversación y genera un resumen breve"
      output: resumen
  - save_document "Resumen" "resumen" resumen
```

## 3. Sintaxis del Script

Dentro de la clave `script` (o dentro de cualquier estrategia), puedes usar la siguiente sintaxis:

### Variables y Formato (F-Strings)
Puedes interpolar cualquier variable de los `slots` directamente en los textos usando llaves `{}`:
```text
say "Tu nombre es {nombre} y tu idioma es {idioma}."
```

### Comentarios
Usa `#` al inicio de la línea para ignorarla:
```text
# Esto es un comentario y el intérprete lo saltará
say "Esto sí se ejecuta"
```

### Encadenamiento de Comandos (Pipes `|`)
Puedes encadenar comandos en una sola línea usando `|`. El resultado del comando anterior (su `value`) se inyecta automáticamente en el siguiente comando como si fuera un argumento adicional (usando el flag interno `is_continuation`).
```text
# Escucha, pasa el texto a una función de Python, y luego muestra el resultado
listen texto | .limpiar_texto | say
```

### Atajos para Ejecutar Funciones (Dot-commands)
Si tienes una función en tus `plugins` llamada `calcular_edad`, no necesitas escribir `exec calcular_edad`. Puedes usar el prefijo `.`:
```text
# Equivale a: exec calcular_edad 1990
.calcular_edad 1990
```

## 4. Control de Flujo (If / While)

Puedes agregar guardas `if` o `while` antes de cualquier comando simple.

**Sintaxis:** `[if|while] <condición> then <comando>`

### Operadores Lógicos
*   **Operadores:** `==`, `!=`, `<`, `>`, `<=`, `>=`
*   **Negación:** Usa `not` antes de la variable.
*   **Disyunción:** Usa `or` para unir cláusulas.
*   **Cadenas de texto:** Usa comillas dobles o simples en las comparaciones para no confundirlas con variables.

```text
# If simple
if idioma == "es" then say "¡Hola!"

# If con negación
if not status == "ok" then solve manejo_errores

# If con or y comillas
if intentos > 3 or nombre == "Desconocido" then say "Fin del programa."

# While (Cuidado con los bucles infinitos)
while intentos < 3 then listen entrada

# While con solve: cada vez que la condición sea verdadera, la estrategia
# completa se ejecuta de principio a fin (incluyendo sus propios if/while)
# antes de volver a evaluar la condición.
while _status == "continue" then solve main_loop
```

> **Importante:** el comando guardado por `while` se ejecuta **por completo** en cada
> vuelta antes de revisar la condición otra vez. Si usas `while ... then solve estrategia`,
> asegúrate de que esa estrategia modifique (con `set`, `llm_extract`, etc.) la variable
> que aparece en la condición; si nunca cambia, el bucle nunca terminará (hasta el límite
> de seguridad de iteraciones).

## 5. Limpieza y análisis en segundo plano (`cleanup`)

La clave opcional `cleanup` en `main.yaml` define un script que se ejecuta **una sola vez, en
segundo plano, cuando la sesión termina** (el usuario cierra la conexión, se desconecta, o el
script principal termina). No es parte del flujo normal: nadie lo ve en tiempo real y no bloquea
el cierre de la conversación (corre en su propio hilo, desacoplado de la sesión).

La idea principal es usarlo para **analizar la conversación completa** con `llm`/`llm_extract`
(tienen acceso a todo el historial de mensajes) y:
* guardar el resultado como un **documento** adjunto a la conversación, con `save_document`;
* y/o etiquetar la conversación completa según ese análisis, con `tag_conversation`.

Ambos quedan visibles después en la ficha de la conversación.

```yaml
cleanup:
  - llm_extract:
      system: analizar_sentimiento
      user: "Analiza el sentimiento general del usuario en esta conversación"
      output: sentimiento
  - save_document "Sentimiento" "sentimiento" sentimiento
  - if sentimiento == "negativo" then tag_conversation revisar_urgente

  - llm "Resume esta conversación en un párrafo" | save_document "Resumen" "resumen"
```

Dentro de `cleanup` puedes usar cualquier comando (`if`/`while`/`solve`/`exec`, etc.), pero no hay
un usuario esperando: si el script llama a `listen`, no se bloquea -- simplemente recibe una
cadena vacía inmediatamente y continúa.

## 6. Referencia de Comandos

### `say <clave_plantilla | texto>`
Muestra un mensaje al usuario. Si el argumento coincide con una clave en tus archivos de `templates`, usa esa plantilla (con soporte para casos aleatorios). Si no, lo interpreta como texto literal.
```text
say "Bienvenido"
say saludo_inicial  # Busca en la lista de templates cargadas
```

### `listen <variable>`
Detiene la ejecución, espera la entrada del usuario (a través del `callback`) y la guarda en la variable indicada.
```text
listen email_usuario
```

### `set <variable> [valor1 valor2 ...]`
Asigna un valor a una variable. Si pasas **un solo valor**, se guarda tal cual (como texto o número, comparable directamente en un `if`/`while`). Si pasas **varios valores**, se guardan como una lista. Si se usa encadenado con `|`, captura el resultado del comando anterior.
```text
set edad 25
set _status "continue"          # _status queda como el texto "continue"
set colores rojo verde azul     # colores queda como ["rojo", "verde", "azul"]
listen texto | set texto_limpio  # texto_limpio obtiene lo que se escuchó

# Útil para controlar un while:
while _status == "continue" then solve main_loop
```

### `llm <clave_prompt | texto> [variable]`
Envía un prompt al Modelo de Lenguaje (LLM). 
* Si solo pasas un argumento, muestra la respuesta al usuario.
* Si pasas dos argumentos, guarda la respuesta en la variable indicada (actualizando el contexto para futuros usos).
```text
llm "Dime un chiste corto"
llm prompt_resumen texto_usuario  # Guarda la respuesta en el slot 'prompt_resumen'
```

### `llm_extract <clave_prompt | texto> [variable]`
Envía un prompt al LLM pidiéndole una respuesta **estructurada** (JSON) en lugar de texto libre, y guarda lo extraído en slots. Acepta dos formas:

**Forma posicional** (una sola línea):
```text
llm_extract extract_info "{respuesta_usuario}" finished
```

**Forma de bloque** (recomendada cuando necesitas prompts de `system` y `user` por separado):
```yaml
- llm_extract:
    system: extract_info
    user: "{respuesta_usuario}"
    output: finished
```

* `system` / `user` se resuelven igual que en `llm`: primero se busca la clave en `prompts`, si no existe se usa el texto tal cual (con `{slots}` interpolados).
* `output` (o el segundo argumento en la forma posicional) nombra el slot donde se guarda el resultado:
  * Si el LLM devuelve un único valor (p. ej. `{"finished": true}`), `output` queda como ese valor escalar (`finished == true`), listo para usarse en un `if`/`while`.
  * Si el LLM devuelve varios campos, `output` queda como el objeto completo (un diccionario). Las condiciones (`if`/`while`) no soportan acceder a un campo interno con punto (`finished.campo`); en ese caso omite `output` para que cada campo se guarde como su propio slot.
* Si **no** se indica `output`, cada campo que devuelva el LLM se guarda directamente como un slot con su propio nombre (útil para extraer varios datos sueltos a la vez).

```text
# Termina el bucle cuando el LLM decide que la conversación acabó
- llm_extract:
    system: extract_info
    user: "Termina"
    output: finished
- if finished == true then set _status "stop"
```

### `sleep <segundos>`
Pausa la ejecución del script (de forma síncrona) durante el número de segundos indicado.
```text
sleep 2
```

### `solve <nombre_estrategia | nombre_conversacion>`
Salta a otro flujo. 
* Si es una **estrategia**, la ejecuta y vuelve a la línea siguiente.
* Si es una **sub-conversación**, pausa el flujo actual, ejecuta el otro archivo por completo, y espera a que use `return` para recuperar datos.
```text
solve manejo_errores
solve auth_flow
```

### `return <variable>`
Usado dentro de una sub-conversación. Toma el valor de la variable indicada y lo empaqueta para devolvérselo al flujo padre que llamó a `solve`.
```text
set token "abc123"
return token
```

### `exec <funcion> [arg1, arg2, ...]`
Ejecuta una función de Python que haya sido cargada desde la carpeta `plugins`. Los argumentos son evaluados antes de pasarlos (puedes usar variables o expresiones matemáticas).
```text
exec calcular_precio 100 "{descuento}"
```

### `remember <variable> <valor>`
Guarda un par clave-valor de forma persistente en la base de datos (usando `SqlAlchemyMemoryStore`), asociado al usuario y proyecto actuales.
```text
remember preferencia_color "azul"
```

### `save_document <título> <tipo> [variable] [etiqueta1 etiqueta2 ...]`
Adjunta un **documento** (p. ej. un análisis generado por LLM) a la conversación actual, visible
después en su ficha. Pensado sobre todo para usarse dentro de `cleanup`, después de `llm`/
`llm_extract`. Acepta dos formas:

**Forma posicional:**
* Si das un tercer argumento, toma el contenido del slot con ese nombre. Cualquier token
  adicional después de ese se guarda como etiqueta del documento.
* Si omites el tercer argumento, toma el resultado del comando anterior en la cadena (`|`)
  (en ese caso no puedes pasar etiquetas -- usa la forma de bloque).
```text
llm_extract:
  system: analizar_sentimiento
  user: "..."
  output: sentimiento
save_document "Sentimiento" "sentimiento" sentimiento positivo revisado

# o encadenado (sin etiquetas):
llm "Resume esta conversación" | save_document "Resumen" "resumen"
```

**Forma de bloque** (necesaria si quieres etiquetas junto con `|`, o prefieres ser explícito):
```yaml
- save_document:
    title: "Sentimiento"
    kind: "sentimiento"
    variable: sentimiento
    tags: [positivo, revisado]
```

### `list_documents [variable]`
Lista los documentos adjuntados con `save_document` a lo largo de **todas** las ejecuciones de este script por el usuario actual (no solo la sesión en curso), ordenados del más reciente al más antiguo por fecha de actualización. Cada entrada trae `uuid`, `title`, `created_at` y `updated_at` (sin `content`; usa `load_document` para obtener el contenido de uno en concreto).
```text
list_documents documentos
```

### `load_document <uuid_o_título> [variable]`
Carga un documento adjuntado previamente con `save_document`. La estrategia de búsqueda se detecta automáticamente a partir del primer argumento: si es un `uuid` válido, busca ese documento exacto; si no, lo trata como un título y carga la versión más reciente con ese título (entre todas las ejecuciones de este script por el usuario actual).
```text
load_document "Resumen" resumen_anterior
say "{resumen_anterior[content]}"

# o por uuid exacto
load_document "019ff7fe-f296-7967-9bc8-09c5b35d9001" documento
```

### `info <tipo1, tipo2, ...>`
Comando de diagnóstico que yielda (envía) metadatos a la interfaz. Tipos válidos: `slots`, `name`, `strategies`, `status`.
```text
info slots
info name, status
```

### `tag <etiqueta1, etiqueta2, ...>`
Añade etiquetas analíticas al flujo de la conversación (útil para dividir el log en secciones posteriormente). Estas etiquetas son parte del *stream* en tiempo real, no se guardan en la ficha de la conversación.
```text
tag inicio_conversacion
tag fase_auth, validacion_email
```

### `tag_conversation <etiqueta1> [etiqueta2, ...]`
A diferencia de `tag`, esto añade etiquetas a la **conversación completa**, persistidas en su ficha (las mismas que se ven y editan como chips en las tarjetas/vista de conversación). Útil dentro de `cleanup` para etiquetar automáticamente según el resultado de un análisis.
```text
if sentimiento == "negativo" then tag_conversation revisar_urgente

tag_conversation revisado auto
```
