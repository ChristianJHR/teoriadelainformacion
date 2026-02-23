# Bitácora

---

## Formatos de información

- **Texto** → ASCII, UTF-8, ÚNICO DE  
- **Numérico** → Decimal, Binario, Octal, Hexadecimal  
- **Imagen** → PNG, JPG, GIF, SVG  
- **Video** → MP4, MKV  
- **Audio** → MP3, WAV  

---

# ¿Cómo interpretan las computadoras cada formato?

## 1. Texto (Diccionarios)

La computadora no sabe qué es una "A".  
Usa un índice numérico.

**ASCII / UTF-8**:  
Son tablas de equivalencia.  
Si la computadora ve el número `65`, sabe que debe mostrar la letra **A**.

---

## 2. Números (Matemáticas Puras)

Es su lenguaje nativo.

- **Binario**: La base de todo (`0` y `1`).  
- **Hexadecimal / Octal**: Son formas más cortas de escribir números binarios largos para que los humanos no nos confundamos.

---

## 3. Imágenes (Puntos o Instrucciones)

- **PNG / JPG / GIF**:  
  La computadora ve una rejilla de puntos (píxeles).  
  Cada punto tiene un código de color.  

  **Ejemplo:**  
  - Rojo = 255  
  - Verde = 0  
  - Azul = 0  

- **SVG**:  
  La computadora lee instrucciones matemáticas.  

  **Ejemplo:**  
  "Dibuja una línea de A hasta B".

---

## 4. Video (Contenedores)

- **MP4 / MKV**:  
  Son como "cajas".  
  La computadora extrae de la caja:
  - Una pista de imágenes  
  - Una pista de sonido  

  Y las reproduce al mismo tiempo.

---

## 5. Audio (Ondas)

- **WAV / MP3**:  
  La computadora toma "fotos" de la onda de sonido miles de veces por segundo y guarda el valor de su altura.

- **MP3**:  
  Borra los sonidos que tus oídos no alcanzan a notar para ahorrar espacio.

---

# Sistema de Comunicación

- **Emisor**
- **Receptor**
- **Medio de comunicación**
- **Protocolo (Sintaxis)** → Conjunto de reglas
- **Código (Abecedario)**
- **Mensaje (Datos)** → Significado

---

# Estados de la Información

- **En uso**
- **En tránsito**
- **En reposo**
  - Base de datos  
  - Archivo  
  - Nube  
  - Disco duro  

---

# DB Engine

## SQL

### Relacionales
- MySQL  
- PostgreSQL  
- MariaDB  
- SQL Server  

## NoSQL
- Elastic  
- MongoDB  
- Cassandra  

---

# SQL Injection

## Ejemplos de consultas SQL

```sql
SELECT * FROM users;

SELECT username, password FROM user;

SELECT username, password 
FROM user 
WHERE username = "peter" 
AND password = "12345";

SELECT username, password 
FROM user 
WHERE username = "" OR 1=1 -- 
AND password = "abcdefg";
```

## Ejemplos de Ataques

```text
username: " OR 1=1 --
password: ********
```

```php
$user = "peter";
$password = "123456";
```

# Seguridad

## Capas

- WEB
- APPLICATION
- FIREWALL

## Medidas de protección

- Sanitización
- Parametrización
- Procedimientos almacenados

## Referencias

- Top Ten
- OWASP
