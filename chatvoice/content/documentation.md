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
```

## 5. Referencia de Comandos

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
Asigna un valor a una variable. Si le pasas múltiples valores, los guardará como una lista. Si se usa encadenado con `|`, captura el resultado del comando anterior.
```text
set edad 25
set colores rojo verde azul
listen texto | set texto_limpio  # texto_limpio obtiene lo que se escuchó
```

### `llm <clave_prompt | texto> [variable]`
Envía un prompt al Modelo de Lenguaje (LLM). 
* Si solo pasas un argumento, muestra la respuesta al usuario.
* Si pasas dos argumentos, guarda la respuesta en la variable indicada (actualizando el contexto para futuros usos).
```text
llm "Dime un chiste corto"
llm prompt_resumen texto_usuario  # Guarda la respuesta en el slot 'prompt_resumen'
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

### `info <tipo1, tipo2, ...>`
Comando de diagnóstico que yielda (envía) metadatos a la interfaz. Tipos válidos: `slots`, `name`, `strategies`, `status`.
```text
info slots
info name, status
```

### `tag <etiqueta1, etiqueta2, ...>`
Añade etiquetas analíticas al flujo de la conversación (útil para dividir el log en secciones posteriormente).
```text
tag inicio_conversacion
tag fase_auth, validacion_email
```
