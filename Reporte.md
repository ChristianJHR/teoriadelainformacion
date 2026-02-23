# REPORTE TÉCNICO COMPLETO - PROYECTO SOC PLATFORM
**Implementación de Wazuh + TheHive + Cortex + MISP**

---

## RESUMEN

Este documento detalla la implementación completa de una plataforma SOC (Security Operations Center) integrando cuatro herramientas de seguridad open-source: Wazuh (SIEM), TheHive (gestión de casos), Cortex (análisis automatizado) y MISP (threat intelligence). El documento cubre desde la preparación del entorno hasta la prueba de concepto final, incluyendo todos los errores encontrados y sus soluciones.

**Estado Final:** ✅ Completamente funcional e integrado

---

## OBJETIVOS DEL PROYECTO

- Implementar Wazuh como SIEM principal para detección de amenazas
- Configurar TheHive para gestión de incidentes y casos
- Integrar Cortex para análisis automatizado de observables
- Incorporar MISP para inteligencia de amenazas compartida
- Integrar las 4 plataformas en un ecosistema SOC funcional

---

## ESPECIFICACIONES TÉCNICAS

### Infraestructura

- **Sistema Operativo:** Ubuntu Server 24.04 LTS
- **RAM:** 8GB
- **Disco:** 100GB (crítico — inicialmente se intentó con 60GB causando fallos)
- **CPUs:** 2–4 cores
- **Red:** Bridge mode (no NAT)
- **Acceso:** SSH desde Cygwin (Windows)

### Arquitectura de Deployment

- **Wazuh:** Instalación nativa en el sistema (puertos 443, 1514, 1515, 55000)
- **TheHive + Cortex:** Docker Compose (puertos 9000, 9001)
- **MISP:** Docker Compose separado (puertos 8080, 8443)

### Resumen de Puertos

| Servicio | Puerto |
|---|---|
| Wazuh | 443, 1514, 1515, 55000 |
| TheHive | 9000 |
| Cortex | 9001 |
| MISP | 8443 |
| Elasticsearch (TheHive) | 9201 |
| Cassandra | 9042 |

---

## GUÍA DE INSTALACIÓN PASO A PASO

> Esta sección documenta el proceso completo de instalación ejecutado, con todos los comandos utilizados.

### PASO 1: Preparar Ubuntu Server

Conectarse a la VM desde Cygwin:
```bash
ssh chris@IP-DE-TU-VM
```

Configurar el sistema:
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Configurar hostname y DNS
sudo hostnamectl set-hostname soc-platform
echo "127.0.0.1 soc-platform" | sudo tee -a /etc/hosts
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf

# Reiniciar
sudo reboot
```

Reconectarse tras el reinicio:
```bash
ssh chris@IP-DE-TU-VM
```

---

### PASO 2: Instalar Docker

```bash
# Instalar Docker
sudo apt install -y docker.io docker-compose

# Iniciar y habilitar
sudo systemctl start docker
sudo systemctl enable docker

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER
```

Cerrar sesión y reconectarse para aplicar el grupo:
```bash
exit
ssh chris@IP-DE-TU-VM
```

Verificar instalación:
```bash
docker --version
docker ps
```

---

### PASO 3: Instalar Wazuh

```bash
cd ~
curl -sO https://packages.wazuh.com/4.7/wazuh-install.sh
sudo bash ./wazuh-install.sh -a -i
```

> ⚠️ **Nota:** El flag `-i` es necesario para ignorar la validación de sistema operativo (Ubuntu 24.04 no es reconocido de forma nativa por el instalador).

> **IMPORTANTE:** Guardar las credenciales que aparecen al finalizar la instalación:
> ```
> User: admin
> Password: [ANOTAR AQUÍ]
> ```

Verificar que Wazuh esté corriendo:
```bash
sudo systemctl status wazuh-dashboard
sudo systemctl status wazuh-manager
sudo systemctl status wazuh-indexer
```

Acceder al dashboard: `https://IP-DE-TU-VM`

---

### PASO 4: Instalar TheHive y Cortex

Crear estructura de directorios:
```bash
mkdir -p ~/soc-platform
cd ~/soc-platform

# Crear directorios para datos persistentes
mkdir -p data/{elasticsearch,cassandra,cortex,thehive}

# Arreglar permisos (IMPORTANTE — sin esto los contenedores fallan)
sudo chown -R 1000:1000 data/
sudo chmod -R 755 data/
```

Crear el archivo `docker-compose.yml`:
```bash
nano docker-compose.yml
```

Contenido del archivo (con fix de puerto para evitar conflicto con Wazuh):
```yaml
version: '3.8'

services:
  elasticsearch:
    image: elasticsearch:7.17.9
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - cluster.name=thehive
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    volumes:
      - ./data/elasticsearch:/usr/share/elasticsearch/data
    ports:
      - "9201:9200"  # Puerto 9201 para evitar conflicto con Wazuh (usa 9200)
    networks:
      - soc-network
    restart: unless-stopped

  cassandra:
    image: cassandra:4.0
    container_name: cassandra
    environment:
      - MAX_HEAP_SIZE=512M
      - HEAP_NEWSIZE=128M
    volumes:
      - ./data/cassandra:/var/lib/cassandra
    ports:
      - "9042:9042"
    networks:
      - soc-network
    restart: unless-stopped

  thehive:
    image: strangebee/thehive:5.2
    container_name: thehive
    depends_on:
      - cassandra
    ports:
      - "9000:9000"
    environment:
      - TH_NO_CONFIG_CORTEX=1
      - CQL_HOSTNAMES=cassandra
      - CQL_USERNAME=cassandra
      - CQL_PASSWORD=cassandra
    volumes:
      - ./data/thehive:/opt/thp/thehive/data
    networks:
      - soc-network
    restart: unless-stopped

  cortex:
    image: thehiveproject/cortex:3.1.7
    container_name: cortex
    depends_on:
      - elasticsearch
    ports:
      - "9001:9001"
    volumes:
      - ./data/cortex:/var/cortex
    networks:
      - soc-network
    restart: unless-stopped

networks:
  soc-network:
    driver: bridge
```

Guardar con `Ctrl+O`, `Enter`, `Ctrl+X`.

Levantar los servicios:
```bash
docker-compose up -d
```

Esperar 5 minutos y verificar que todos estén `Up`:
```bash
docker-compose ps
```

---

### PASO 5: Instalar MISP

```bash
# Crear directorio para MISP
sudo mkdir -p /opt/misp-docker
cd /opt/misp-docker

# Crear docker-compose.yml
sudo nano docker-compose.yml
```

Contenido del archivo (incluye el fix del bug `CRON_USER_ID`):
```yaml
version: '3'

services:
  redis:
    image: redis:6-alpine
    container_name: misp-redis
    restart: always

  db:
    image: mariadb:10.11
    container_name: misp-db
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: misp_root
      MYSQL_DATABASE: misp
      MYSQL_USER: misp
      MYSQL_PASSWORD: misp_pass
    volumes:
      - mysql_data:/var/lib/mysql
    command: --default-authentication-plugin=mysql_native_password --innodb-buffer-pool-size=256M

  misp-core:
    image: coolacid/misp-docker:core-latest
    container_name: misp-core
    depends_on:
      - redis
      - db
    ports:
      - "8080:80"
      - "8443:443"
    environment:
      MYSQL_HOST: db
      MYSQL_PORT: 3306
      MYSQL_DATABASE: misp
      MYSQL_USER: misp
      MYSQL_PASSWORD: misp_pass
      MISP_ADMIN_EMAIL: admin@admin.test
      MISP_ADMIN_PASSPHRASE: admin
      MISP_BASEURL: https://localhost:8443
      REDIS_FQDN: redis
      TIMEZONE: UTC
      INIT: "true"
      DISABLE_IPV6: "true"
      CRON_USER_ID: "33"   # FIX del bug en coolacid/misp-docker
    volumes:
      - misp_data:/var/www/MISP
    restart: always

volumes:
  mysql_data:
  misp_data:
```

Guardar con `Ctrl+O`, `Enter`, `Ctrl+X`.

Levantar MISP:
```bash
sudo docker-compose up -d
```

Monitorear la inicialización (tarda 10–15 minutos):
```bash
sudo docker logs misp-core -f
```

Esperar hasta ver mensajes estables y presionar `Ctrl+C` para salir del log.

Acceder: `https://IP-DE-TU-VM:8443`

---

### PASO 6: Integrar Cortex con TheHive

#### A) Configuración en Cortex (`http://IP-VM:9001`)

1. Abrir Cortex y hacer clic en **"Update Database"**
2. Crear usuario administrador inicial
3. Iniciar sesión
4. Ir a **Organization** → **"+"** → Nombre: `SOC-Org`
5. Ir a **Users** → **"Create User"**:
   - Login: `thehive-integration`
   - Roles: `read`, `analyze`
   - Organization: `SOC-Org`
6. Hacer clic en **"Create API Key"** → **copiar el key generado**

#### B) Configuración en TheHive (`http://IP-VM:9000`)

1. Iniciar sesión: `admin@thehive.local` / `secret`
2. Hacer clic en el ícono de engranaje (arriba a la derecha)
3. Ir a **Entities** → **Cortex** → **"+"**
4. Completar configuración:
   - **Name:** `Cortex-Main`
   - **URL:** `http://cortex:9001`
   - **Auth Type:** `Bearer`
   - **API Key:** [pegar el key copiado de Cortex]
5. Hacer clic en **Test** → **Confirm**

**Resultado:** ✅ TheHive puede ejecutar analyzers de Cortex en observables

---

### PASO 7: Integrar MISP con TheHive

#### A) Obtener API Key en MISP (`https://IP-VM:8443`)

1. Iniciar sesión: `admin@admin.test` / `admin`
2. **Importante:** Cambiar la contraseña por defecto primero
3. Ir a **Event Actions** → **Automation**
4. Hacer clic en el enlace **"here"** al final del segundo párrafo (lleva a la página de API keys)
5. Hacer clic en **"Auth keys"**
6. Hacer clic en **"Add authentication key"** (o **"+"**)
7. En el formulario:
   - **Comment:** `thehive-integration`
   - **Allowed IPs:** dejar vacío (permite desde cualquier IP)
   - **Expiration:** dejar vacío (sin expiración)
   - **Read only:** NO marcar
8. Hacer clic en **Submit**
9. **Copiar el API key inmediatamente** — MISP solo lo muestra una vez

> ⚠️ Si ya existe una key creada, MISP solo muestra los primeros y últimos 3 caracteres por seguridad. En ese caso, crear una nueva key con el formulario.

#### B) Configuración en TheHive (`http://IP-VM:9000`)

1. Ir a **Admin** → **Platform Management** → **MISP Servers** → **"+"**
2. Completar configuración:
   - **Name:** `MISP`
   - **URL:** `https://misp-core:443`
   - **API Key:** [pegar el key copiado de MISP]
   - **Purpose:** seleccionar `ImportOnly` y `ExportOnly`
   - **Check Certificate Authority:** Disabled (toggle en OFF)
   - **Disable hostname Verification:** Enabled
3. Hacer clic en **Save** o **Confirm**

**Resultado:** ✅ TheHive puede importar/exportar eventos con MISP

---

## ⚠️ PROBLEMAS ENCONTRADOS Y SOLUCIONES

### PROBLEMA 1: Configuración de Red (NAT vs Bridge)

**Error inicial:**
```
Wazuh dashboard server is not ready yet
No se puede acceder a las interfaces web
```

**Causa raíz:** La VM estaba configurada en modo NAT, lo que requiere port forwarding manual y complica el acceso desde el host.

**Solución aplicada:**
- Cambiar configuración de red de la VM a Bridge mode
- Obtener nueva IP en la misma red que el host
- Verificar con `hostname -I`

**Resultado:** ✅ Acceso directo a todas las interfaces web

---

### PROBLEMA 2: Instalación de Wazuh — Validación de Sistema

**Error inicial:**
```
ERROR: The recommended systems are: Red Hat Enterprise Linux 7, 8, 9; CentOS 7, 8; Amazon Linux 2
```

**Causa raíz:** El script de instalación no reconocía Ubuntu 24.04 como sistema soportado.

**Solución aplicada:**
```bash
sudo bash ./wazuh-install.sh -a -i
```
El flag `-i` (ignore checks) fuerza la instalación ignorando la validación del SO.

**Resultado:** ✅ Wazuh instalado correctamente

---

### PROBLEMA 3: Conflicto de Puertos — Elasticsearch

**Error inicial:**
```
ERROR: Port 9200 is being used by another process
```

**Causa raíz:** Wazuh usa el puerto 9200 para su indexer (OpenSearch), y TheHive necesita Elasticsearch que también usa 9200 por defecto.

**Solución aplicada:** Modificar `docker-compose.yml` de TheHive para usar el puerto 9201:
```yaml
elasticsearch:
  ports:
    - "9201:9200"
```

**Resultado:** ✅ Ambos servicios coexisten sin conflictos

---

### PROBLEMA 4: Permisos de Directorios Docker

**Error inicial:**
```
[ConnectionError]: AccessDeniedException: /var/lib/wazuh-indexer/nodes
```

**Causa raíz:** Los volúmenes de Docker no tenían los permisos correctos para que los contenedores escribieran datos.

**Solución aplicada:**
```bash
sudo chown -R 1000:1000 data/
sudo chmod -R 755 data/
```

**Resultado:** ✅ Contenedores pueden escribir en volúmenes persistentes

---

### PROBLEMA 5: TheHive — Error Interno (Cassandra)

**Error inicial:**
```
An Internal Error Has Occurred
Error: An Internal Error Has Occurred
```

**Causa raíz:** Cassandra tarda varios minutos en inicializar completamente. TheHive intentaba conectarse antes de que estuviera listo.

**Solución aplicada:**

Verificar estado de Cassandra:
```bash
docker exec -it cassandra cqlsh -e "DESCRIBE KEYSPACES;"
```

Agregar variables de entorno en `docker-compose.yml`:
```yaml
thehive:
  environment:
    - CQL_HOSTNAMES=cassandra
    - CQL_USERNAME=cassandra
    - CQL_PASSWORD=cassandra
```

Reiniciar en orden correcto:
```bash
docker-compose restart cassandra
sleep 60
docker-compose restart thehive
```

**Resultado:** ✅ TheHive conecta exitosamente a Cassandra

---

### PROBLEMA 6: MISP — Bug de CRON_USER_ID

**Error crítico:**
```
Error: Format string 'CRON_USER_ID=%(ENV_CRON_USER_ID)s' for 'environment' 
contains names ('ENV_CRON_USER_ID') which cannot be expanded
```

**Causa raíz:** La imagen Docker `coolacid/misp-docker:core-latest` tiene un bug en su archivo `supervisord.conf`. La variable `CRON_USER_ID` es requerida pero no está definida.

**Intentos fallidos antes de encontrar la solución:**
- Imagen `coolacid/misp-docker:core-v2.4.182` → versión no existe
- Imagen `harvarditsecurity/misp` → MySQL interno falla
- Imagen `ghcr.io/misp/misp-docker/misp-core:latest` → mismo error

**Solución definitiva:** Agregar la variable faltante manualmente en `docker-compose.yml`:
```yaml
misp-core:
  environment:
    CRON_USER_ID: "33"  # FIX del bug
```

**Resultado:** ✅ MISP inicia correctamente sin errores

---

### PROBLEMA 7: MISP — Base de Datos No Inicia

**Error inicial:**
```
ERROR 2002 (HY000): Can't connect to MySQL server on 'db' (115)
```

**Causa raíz:** MariaDB necesitaba más tiempo para inicializar y crear las tablas necesarias.

**Solución aplicada:** Configuración optimizada de MariaDB:
```yaml
db:
  image: mariadb:10.11
  command: --default-authentication-plugin=mysql_native_password --innodb-buffer-pool-size=256M
```

**Resultado:** ✅ MISP conecta exitosamente a la base de datos

---

### PROBLEMA 8: Sin Espacio en Disco (Crítico)

**Error recurrente:**
```
ERROR: mariadbd: Error writing file './ddl_recovery.log' 
(Errcode: 28 "No space left on device")
```

**Causa raíz:** El disco de 60GB se llenó rápidamente:
- Imágenes Docker: ~20GB
- Volúmenes de datos: ~15GB
- Logs del sistema: ~10GB
- Sistema base: ~10GB

**Solución inmediata — limpieza:**
```bash
docker system prune -a --volumes -f
sudo journalctl --vacuum-time=1d
sudo apt clean
```

**Solución permanente — ampliar disco a 100GB y expandir partición:**
```bash
# (Ampliar el disco desde VirtualBox/VMware primero)
sudo growpart /dev/sda 3
sudo resize2fs /dev/sda3
df -h  # Verificar nuevo tamaño
```

**Resultado:** ✅ Espacio suficiente para operación estable

---

### PROBLEMA 9: Hostname Resolution (DNS)

**Error inicial:**
```
sudo: unable to resolve host soc-plataform: Name or service not known
```

**Causa raíz:** El hostname no estaba registrado en `/etc/hosts`.

**Solución aplicada:**
```bash
echo "127.0.0.1 soc-plataform" | sudo tee -a /etc/hosts
```

**Resultado:** ✅ Warnings eliminados

---

## TABLA DE ACCESOS

| Servicio | URL | Usuario | Password | Puerto |
|---|---|---|---|---|
| Wazuh | `https://IP-VM` | admin | [guardada en instalación] | 443 |
| TheHive | `http://IP-VM:9000` | admin@thehive.local | secret | 9000 |
| Cortex | `http://IP-VM:9001` | [creado en setup] | [creado en setup] | 9001 |
| MISP | `https://IP-VM:8443` | admin@admin.test | admin | 8443 |

---

## PRUEBA DE CONCEPTO — FLUJO COMPLETO SOC

### Escenario

Detectar intentos de acceso SSH fallidos → Crear caso en TheHive → Analizar con Cortex → Buscar en MISP → Documentar y cerrar

### Qué hace cada herramienta en este flujo

**Wazuh** actúa como el detector: monitorea logs del sistema en tiempo real y genera alertas ante actividad sospechosa como logins fallidos, cambios en archivos críticos, vulnerabilidades y comportamiento anómalo. Es el SIEM que alimenta toda la operación del SOC.

**TheHive** gestiona el caso: organiza la investigación, permite agregar observables y tareas, lleva el estado del incidente y facilita la colaboración entre analistas.

**Cortex** analiza la evidencia: ejecuta analyzers automatizados sobre IPs, hashes, URLs y otros observables para enriquecer la investigación con datos de fuentes externas como VirusTotal o AbuseIPDB.

**MISP** aporta inteligencia: permite verificar si los indicadores encontrados ya están en bases de datos de amenazas conocidas y compartir nueva inteligencia con la comunidad.

---

### Paso 1 — Generar una alerta en Wazuh

> ⚠️ **Importante:** No cerrar la sesión SSH actual. Abrir una **nueva ventana de Cygwin** o generar la alerta con `sudo` desde la sesión existente.

Opción A — Desde nueva ventana de Cygwin:
```bash
ssh usuario_falso@IP-DE-TU-VM
# Escribir contraseñas incorrectas 5 veces seguidas
```

Opción B — Desde la sesión SSH actual (más sencillo):
```bash
sudo ls
# Escribir contraseña incorrecta 3 veces
```

### Paso 2 — Ver la alerta en Wazuh

1. Ir a `https://IP-VM`
2. En el menú lateral: **Wazuh** → **Threat Hunting** → **Security events**
3. Buscar alertas de `Authentication failed` o `sshd`
4. Hacer clic en una alerta para ver los detalles
5. Anotar la IP de origen (será `127.0.0.1` o `::1`)

### Paso 3 — Crear un caso en TheHive

1. Ir a `http://IP-VM:9000`
2. Hacer clic en **"+ New case"**
3. Completar:
   - **Title:** `Intento de acceso SSH sospechoso`
   - **Severity:** `Medium`
   - **TLP:** `Amber`
   - **Description:** `Múltiples intentos fallidos de SSH desde IP: 127.0.0.1`
4. Hacer clic en **Confirm**

### Paso 4 — Agregar observable y analizar con Cortex

Dentro del caso creado:

1. Ir a la pestaña **"Observables"**
2. Hacer clic en **"+ Add observable"**:
   - **Type:** `ip`
   - **Value:** `127.0.0.1`
3. Hacer clic en **Confirm**
4. Hacer clic en los **3 puntos** al lado del observable
5. Seleccionar **"Run analyzers"**
6. Marcar los analyzers disponibles y hacer clic en **Run**
7. Esperar los resultados del análisis

### Paso 5 — Buscar en MISP (opcional)

1. En la pestaña **Observables** del caso
2. Hacer clic en los **3 puntos** del observable
3. Seleccionar **"Search in MISP"**
4. Verificar si la IP aparece en eventos de amenazas conocidas

### Paso 6 — Cerrar el caso

1. Ir a la pestaña **"Tasks"** del caso
2. Crear tarea: `Investigación completada` → marcarla como completada
3. Cambiar el estado del caso a **Resolved**
4. Agregar nota final: `Acceso local, falsa alarma — ambiente de prueba`

### Resultado del flujo

| Paso | Herramienta | Estado |
|---|---|---|
| Detección de amenaza | Wazuh | ✅ |
| Gestión del caso | TheHive | ✅ |
| Análisis de observable | Cortex | ✅ |
| Búsqueda de inteligencia | MISP | ✅ |
| **Flujo SOC completo** | — | ✅ |

---

## RECURSOS DEL SISTEMA

### Uso de RAM (aproximado)

| Servicio | RAM |
|---|---|
| Wazuh | ~2.5GB |
| TheHive + Cassandra | ~2GB |
| Cortex + Elasticsearch | ~1.5GB |
| MISP (Redis + MariaDB + Core) | ~1.5GB |
| Sistema Ubuntu | ~500MB |
| **Total** | **~8GB** |

### Uso de Disco

| Componente | Espacio |
|---|---|
| Imágenes Docker | ~25GB |
| Volúmenes de datos | ~20GB |
| Sistema y logs | ~15GB |
| Espacio libre recomendado | ~40GB |
| **Total recomendado** | **100GB** |

---

## COMANDOS DE MANTENIMIENTO

### Ver estado de servicios

```bash
# Wazuh
sudo systemctl status wazuh-manager
sudo systemctl status wazuh-indexer
sudo systemctl status wazuh-dashboard

# TheHive/Cortex
cd ~/soc-platform
docker-compose ps

# MISP
cd /opt/misp-docker
sudo docker-compose ps
```

### Reiniciar servicios

```bash
# Wazuh
sudo systemctl restart wazuh-dashboard

# TheHive/Cortex
cd ~/soc-platform
docker-compose restart

# MISP
cd /opt/misp-docker
sudo docker-compose restart
```

### Ver logs

```bash
# TheHive
docker logs thehive --tail 100

# Cortex
docker logs cortex --tail 100

# MISP
sudo docker logs misp-core --tail 100

# Cassandra
docker logs cassandra --tail 100
```

### Liberar espacio en disco

```bash
# Limpiar Docker (elimina todo lo no usado — usar con cuidado)
docker system prune -a --volumes -f

# Limpiar logs del sistema
sudo journalctl --vacuum-time=1d

# Limpiar cache de apt
sudo apt clean && sudo apt autoclean

# Ver espacio disponible
df -h
```

---

## SOLUCIÓN DE PROBLEMAS COMUNES

### TheHive muestra "Internal Error"

```bash
cd ~/soc-platform
docker-compose restart cassandra
sleep 60
docker-compose restart thehive
```

### MISP muestra Error 500 o "Not ready"

```bash
cd /opt/misp-docker
sudo docker logs misp-core --tail 100
sudo docker logs misp-db --tail 100

# Si aparece "No space left on device":
docker system prune -a --volumes -f
```

### Sin espacio en disco

```bash
# Ampliar el disco desde VirtualBox/VMware a 100GB, luego:
sudo growpart /dev/sda 3
sudo resize2fs /dev/sda3
df -h
```

### Cassandra no inicia o no responde

```bash
# Verificar conectividad
docker exec -it cassandra cqlsh -e "DESCRIBE KEYSPACES;"

# Si falla, reiniciar y esperar más tiempo
docker-compose restart cassandra
sleep 120
```

---

## MEJORAS FUTURAS RECOMENDADAS

### Corto Plazo

- Configurar backups automáticos de volúmenes Docker
- Implementar monitoreo de recursos (Prometheus + Grafana)
- Agregar agentes Wazuh en otras VMs para monitoreo real

### Mediano Plazo

- Migrar a infraestructura con más recursos (16GB RAM, 200GB disco)
- Implementar alta disponibilidad para servicios críticos
- Configurar alertas automatizadas (email, Slack)
- Agregar más analyzers a Cortex (VirusTotal, AbuseIPDB, etc.)

### Largo Plazo

- Migrar a Kubernetes para mejor orquestación
- Implementar CI/CD para actualizaciones automatizadas
- Integrar feeds de threat intelligence adicionales en MISP

---

## REFERENCIAS Y DOCUMENTACIÓN

### Documentación Oficial

- **Wazuh:** https://documentation.wazuh.com/
- **TheHive:** https://docs.strangebee.com/thehive/
- **Cortex:** https://github.com/TheHive-Project/Cortex
- **MISP:** https://www.misp-project.org/documentation/

### Recursos Útiles

- **Docker Compose:** https://docs.docker.com/compose/
- **Ubuntu Server:** https://ubuntu.com/server/docs
- **Troubleshooting Docker:** https://docs.docker.com/config/daemon/

---

## CONCLUSIÓN

El proyecto SOC Platform fue implementado exitosamente a pesar de enfrentar múltiples desafíos técnicos. La solución final demuestra:

- ✅ Capacidad de instalación y configuración de herramientas open-source de seguridad
- ✅ Resolución sistemática de problemas complejos de integración
- ✅ Documentación exhaustiva de todo el proceso, desde instalación hasta prueba de concepto
- ✅ Funcionalidad completa del flujo SOC de extremo a extremo

La plataforma está operativa y lista para demostración. Con las mejoras recomendadas puede escalar a un SOC real en producción.

---

## EVIDENCIA

[Ver Imágenes de Evidencia](Imagenes_Evidencia/)
