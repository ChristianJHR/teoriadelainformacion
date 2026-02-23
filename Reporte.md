# REPORTE TÉCNICO COMPLETO - PROYECTO SOC PLATFORM
**Implementación de Wazuh + TheHive + Cortex + MISP**

---

## 📋 RESUMEN

Este documento detalla la implementación exitosa de una plataforma SOC (Security Operations Center) completa integrando cuatro herramientas de seguridad: Wazuh (SIEM), TheHive (gestión de casos), Cortex (análisis automatizado) y MISP (threat intelligence). El proyecto enfrentó múltiples desafíos técnicos que fueron resueltos sistemáticamente.

**Estado Final:** ✅ Completamente funcional e integrado

---

## 🎯 OBJETIVOS DEL PROYECTO

- Implementar Wazuh como SIEM principal
- Configurar TheHive para gestión de incidentes
- Integrar Cortex para análisis automatizado de observables
- Incorporar MISP para inteligencia de amenazas
- Integrar las 4 plataformas en un ecosistema funcional

---

## 🖥️ ESPECIFICACIONES TÉCNICAS

### Infraestructura

- **Sistema Operativo:** Ubuntu Server 24.04 LTS
- **RAM:** 8GB
- **Disco:** 100GB (crítico - inicialmente se intentó con 60GB causando fallos)
- **CPUs:** 2-4 cores
- **Red:** Bridge mode
- **Acceso:** SSH desde Cygwin (Windows)

### Arquitectura de Deployment

- **Wazuh:** Instalación nativa en el sistema (puertos 443, 1514, 1515, 55000)
- **TheHive + Cortex:** Docker Compose (puertos 9000, 9001)
- **MISP:** Docker Compose separado (puertos 8080, 8443)

---

## ⚠️ PROBLEMAS ENCONTRADOS Y SOLUCIONES

### PROBLEMA 1: Configuración de Red (NAT vs Bridge)

**Error inicial:**
```
Wazuh dashboard server is not ready yet
No se puede acceder a las interfaces web
```

**Causa raíz:**
La VM estaba configurada en modo NAT, lo que requiere port forwarding manual y complica el acceso.

**Solución aplicada:**

- Cambiar configuración de red de VM a Bridge mode
- Obtener nueva IP en la misma red que el host
- Verificar con `hostname -I`

**Resultado:** ✅ Acceso directo a todas las interfaces web

---

### PROBLEMA 2: Instalación de Wazuh - Validación de Sistema

**Error inicial:**
```
ERROR: The recommended systems are: Red Hat Enterprise Linux 7, 8, 9; CentOS 7, 8; Amazon Linux 2
```

**Causa raíz:**
El script de instalación no reconocía Ubuntu 24.04 como sistema soportado.

**Solución aplicada:**
```bash
sudo bash ./wazuh-install.sh -a -i
```
Agregar flag `-i` (ignore checks) para forzar instalación en Ubuntu 24.04.

**Resultado:** ✅ Wazuh instalado correctamente

---

### PROBLEMA 3: Conflicto de Puertos - Elasticsearch

**Error inicial:**
```
ERROR: Port 9200 is being used by another process
```

**Causa raíz:**
Wazuh usa el puerto 9200 para su indexer (OpenSearch), y TheHive necesita Elasticsearch que también usa 9200 por defecto.

**Solución aplicada:**
Modificar `docker-compose.yml` de TheHive:
```yaml
elasticsearch:
  ports:
    - "9201:9200"  # Cambiar puerto externo a 9201
```

**Resultado:** ✅ Ambos servicios coexisten sin conflictos

---

### PROBLEMA 4: Permisos de Directorios Docker

**Error inicial:**
```
[ConnectionError]: AccessDeniedException: /var/lib/wazuh-indexer/nodes
```

**Causa raíz:**
Los volúmenes de Docker no tenían los permisos correctos para que los contenedores escribieran datos.

**Solución aplicada:**
```bash
sudo chown -R 1000:1000 data/
sudo chmod -R 755 data/
```

**Resultado:** ✅ Contenedores pueden escribir en volúmenes persistentes

---

### PROBLEMA 5: TheHive - Error Interno (Cassandra)

**Error inicial:**
```
An Internal Error Has Occurred
Error: An Internal Error Has Occurred
```

**Causa raíz:**
Cassandra tarda varios minutos en inicializar completamente. TheHive intentaba conectarse antes de que Cassandra estuviera listo.

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

Reiniciar en orden:
```bash
docker-compose restart cassandra
sleep 60
docker-compose restart thehive
```

**Resultado:** ✅ TheHive conecta exitosamente a Cassandra

---

### PROBLEMA 6: MISP - Bug de CRON_USER_ID

**Error crítico:**
```
Error: Format string 'CRON_USER_ID=%(ENV_CRON_USER_ID)s' for 'environment' 
contains names ('ENV_CRON_USER_ID') which cannot be expanded
```

**Causa raíz:**
La imagen Docker `coolacid/misp-docker:core-latest` tiene un bug en su archivo de configuración de Supervisor. La variable de entorno `CRON_USER_ID` no está definida pero el archivo `supervisord.conf` la requiere.

**Intentos fallidos:**

- Usar imagen `coolacid/misp-docker:core-v2.4.182` (versión no existe)
- Usar imagen `harvarditsecurity/misp` (MySQL interno falla)
- Usar imagen `ghcr.io/misp/misp-docker/misp-core:latest` (mismo error)

**Solución definitiva aplicada:**
Agregar la variable de entorno faltante en `docker-compose.yml`:
```yaml
misp-core:
  image: coolacid/misp-docker:core-latest
  environment:
    # ... otras variables ...
    CRON_USER_ID: "33"  # <-- FIX DEL BUG
```

**Resultado:** ✅ MISP inicia correctamente sin errores

---

### PROBLEMA 7: MISP - Base de Datos No Inicia

**Error inicial:**
```
ERROR 2002 (HY000): Can't connect to MySQL server on 'db' (115)
```

**Causa raíz:**
MariaDB necesitaba más tiempo para inicializar y crear las tablas necesarias.

**Solución aplicada:**
Configuración optimizada de MariaDB en `docker-compose.yml`:
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

**Causa raíz:**
El disco de 60GB se llenó rápidamente con:

- Imágenes Docker (~20GB)
- Volúmenes de datos (~15GB)
- Logs del sistema (~10GB)
- Sistema base (~10GB)

**Soluciones aplicadas:**

Limpieza inmediata:
```bash
docker system prune -a --volumes -f
sudo journalctl --vacuum-time=1d
sudo apt clean
```

Solución permanente — ampliar disco de VM a 100GB mínimo y expandir partición:
```bash
sudo growpart /dev/sda 3
sudo resize2fs /dev/sda3
```

**Resultado:** ✅ Espacio suficiente para operación estable

---

### PROBLEMA 9: Hostname Resolution (DNS)

**Error inicial:**
```
sudo: unable to resolve host soc-plataform: Name or service not known
```

**Causa raíz:**
El hostname no estaba configurado en `/etc/hosts`.

**Solución aplicada:**
```bash
echo "127.0.0.1 soc-plataform" | sudo tee -a /etc/hosts
```

**Resultado:** ✅ Warnings eliminados

---

## 📦 CONFIGURACIÓN FINAL FUNCIONAL

### Docker Compose - TheHive y Cortex

**Ubicación:** `/home/chris/soc-platform/docker-compose.yml`

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
      - "9201:9200"
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

### Docker Compose - MISP

**Ubicación:** `/opt/misp-docker/docker-compose.yml`

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
      CRON_USER_ID: "33"
    volumes:
      - misp_data:/var/www/MISP
    restart: always

volumes:
  mysql_data:
  misp_data:
```

---

## 🔗 INTEGRACIONES CONFIGURADAS

### 1. Cortex ↔ TheHive

**Configuración en Cortex:**

- Crear organización: `SOC-Org`
- Crear usuario API: `thehive-integration`
- Roles: `read`, `analyze`
- Generar API key

**Configuración en TheHive:**

- Entities → Cortex → Add server
- Name: `Cortex-Main`
- URL: `http://cortex:9001`
- Auth Type: `Bearer`
- API Key: [key generada]

**Resultado:** ✅ TheHive puede ejecutar analyzers de Cortex en observables

---

### 2. MISP ↔ TheHive

**Configuración en MISP:**

- Event Actions → Automation → Add authentication key
- Copiar API key generada

**Configuración en TheHive:**

- Admin → Platform Management → MISP Servers
- Name: `MISP`
- URL: `https://misp-core:443`
- API Key: [key de MISP]
- Purpose: `ImportOnly` y `ExportOnly`
- Check Certificate Authority: Disabled
- Disable hostname Verification: Enabled

**Resultado:** ✅ TheHive puede importar/exportar eventos con MISP

---

## ✅ PRUEBA DE CONCEPTO EXITOSA

### Escenario de Prueba

Detectar intentos de acceso SSH fallidos → Crear caso → Analizar → Documentar

### Flujo Ejecutado

**1. Generación de alerta:**
```bash
ssh usuario_falso@localhost
# Intentos fallidos × 5
```

**2. Detección en Wazuh:**
- Navegación: Threat Hunting → Security events
- Alerta identificada: `Authentication failed - sshd`
- IP origen: `127.0.0.1`

**3. Creación de caso en TheHive:**
- Título: `Intento de acceso SSH sospechoso`
- Severity: `Medium`
- TLP: `Amber`
- Observable agregado: IP `127.0.0.1`

**4. Análisis con Cortex:**
- Ejecutar analyzers sobre IP
- Resultados obtenidos y documentados

**5. Búsqueda en MISP:**
- Verificar si IP aparece en eventos conocidos

**6. Resolución:**
- Caso marcado como resuelto
- Conclusión: Falsa alarma - ambiente de prueba

**Estado:** ✅ Flujo completo SOC demostrado exitosamente

---

## 📊 RECURSOS DEL SISTEMA

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

## 🔧 COMANDOS DE MANTENIMIENTO

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

### Limpieza de espacio

```bash
# Limpiar Docker (cuidado, elimina todo lo no usado)
docker system prune -a --volumes -f

# Limpiar logs del sistema
sudo journalctl --vacuum-time=1d

# Limpiar cache de apt
sudo apt clean && sudo apt autoclean
```

---

## 🌐 TABLA DE ACCESOS

| Servicio | URL | Usuario | Password | Puerto |
|---|---|---|---|---|
| Wazuh | `https://IP-VM` | admin | [generada] | 443 |
| TheHive | `http://IP-VM:9000` | admin@thehive.local | secret | 9000 |
| Cortex | `http://IP-VM:9001` | [creado] | [creado] | 9001 |
| MISP | `https://IP-VM:8443` | admin@admin.test | admin | 8443 |

---

## 📝 LECCIONES APRENDIDAS

### 1. Planificación de Recursos

- **Crítico:** 100GB de disco no es negociable
- Los 8GB de RAM están al límite, 16GB sería ideal
- Bridge mode es esencial para simplificar acceso

### 2. Docker en Producción

- Siempre verificar permisos de volúmenes antes de iniciar
- Usar `docker-compose ps` frecuentemente para monitorear
- Los logs son cruciales: `docker logs -f [container]`

### 3. Integración de Herramientas

- Documentar todas las API keys generadas
- Probar conexiones inmediatamente después de configurar
- Deshabilitar SSL verification en ambientes de prueba

### 4. Troubleshooting

- Revisar logs siempre antes de asumir el problema
- Google el error específico (muchos están documentados)
- Verificar espacio en disco ante comportamientos erráticos

### 5. MISP Específico

- Las imágenes Docker de MISP son problemáticas
- La variable `CRON_USER_ID: "33"` es esencial
- MariaDB 10.11 es más estable que MySQL 8.0 para MISP

---

## 🚀 MEJORAS FUTURAS RECOMENDADAS

### Corto Plazo

- Configurar backups automáticos de volúmenes Docker
- Implementar monitoreo de recursos (Prometheus + Grafana)
- Agregar agentes Wazuh en otras VMs para monitoreo real

### Mediano Plazo

- Migrar a infraestructura con más recursos (16GB RAM, 200GB disco)
- Implementar alta disponibilidad para servicios críticos
- Configurar alertas automatizadas (email, Slack)

### Largo Plazo

- Migrar a Kubernetes para mejor orquestación
- Implementar CI/CD para actualizaciones automatizadas
- Agregar más analyzers a Cortex (VirusTotal, AbuseIPDB, etc.)

---

## 📚 REFERENCIAS Y DOCUMENTACIÓN

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

## 🎓 CONCLUSIÓN

El proyecto SOC Platform fue implementado exitosamente a pesar de enfrentar múltiples desafíos técnicos significativos. La solución final demuestra:

- ✅ Capacidad de integración de herramientas open-source de seguridad
- ✅ Resolución sistemática de problemas complejos
- ✅ Documentación exhaustiva del proceso
- ✅ Funcionalidad completa del flujo SOC

La plataforma está lista para demostración y puede ser utilizada como base para un SOC operacional real con las mejoras recomendadas.
