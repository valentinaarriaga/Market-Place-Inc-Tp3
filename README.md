# Market-Place-Inc TP3

## Descripción

Este proyecto consiste en la evolución de un sistema monolítico hacia una arquitectura distribuida basada en microservicios.

El objetivo principal fue resolver problemas de:
- escalabilidad,
- disponibilidad,
- concurrencia,
- desacoplamiento,
- observabilidad,
- y overselling en compras concurrentes.

El sistema implementa:
- comunicación síncrona mediante gRPC,
- comunicación asíncrona mediante RabbitMQ,
- locks distribuidos con Redis,
- monitoreo con Prometheus,
- dashboards con Grafana,
- pruebas de carga con Locust,
- automatización CI/CD con GitHub Actions.

---

# Arquitectura

El sistema está compuesto por los siguientes servicios:

| Servicio | Función |
|---|---|
| orders-service | Gestión de pedidos |
| inventory-service | Gestión de stock |
| catalog-service | Catálogo de productos |
| notifications-service | Consumo de eventos y notificaciones |
| RabbitMQ | Broker de mensajería |
| Redis | Locks distribuidos |
| Prometheus | Recolección de métricas |
| Grafana | Visualización de métricas |

---

# Flujo principal

Cliente → orders-service  
orders-service → inventory-service (gRPC)  
orders-service → RabbitMQ → notifications-service  

---

# Comunicación síncrona y asíncrona

## gRPC (Síncrono)

Se utilizó gRPC para la comunicación entre:
- orders-service
- inventory-service

Ventajas:
- baja latencia,
- tipado fuerte,
- comunicación eficiente.

Archivo proto utilizado:

```proto
service InventoryService {
  rpc ReserveStock (ReserveStockRequest)
  returns (ReserveStockResponse);
}

Comando de generación:

python -m grpc_tools.protoc -I proto \
--python_out=inventory-service \
--grpc_python_out=inventory-service \
proto/inventory.proto


## RabbitMQ (Asíncrono)

RabbitMQ se utilizó para desacoplar:

orders-service
notifications-service

Beneficios:

tolerancia a fallos,
procesamiento desacoplado,
persistencia de mensajes,
mejor disponibilidad.

Configuración utilizada:

durable=True
delivery_mode=2 (PERSISTENT)

---

## Prevención de Overselling

Para evitar condiciones de carrera se implementó un lock distribuido utilizando Redis.

Ejemplo:

r.set(lock_key, "reserved", nx=True, ex=5)

Esto garantiza que múltiples usuarios no puedan modificar simultáneamente el mismo stock.

---

## Métricas y observabilidad

El sistema expone métricas Prometheus mediante:

/metrics

Métricas implementadas:

reserve_attempts_total
reserve_duration_seconds
overselling_attempts_total
inventory_stock_level

Grafana permite visualizar:

intentos de reserva,
stock disponible,
overselling,
tiempos de respuesta.

---

## Tests concurrentes

Se implementaron pruebas concurrentes utilizando:

pytest
ThreadPoolExecutor

Escenarios probados:

2 usuarios comprando 1 producto,
50 usuarios comprando 10 productos,
validación de ausencia de overselling,
validación de disponibilidad.

---

## Load Testing

Se utilizó Locust para simular múltiples usuarios concurrentes.

Ejemplo:

50 usuarios simultáneos,
múltiples reservas concurrentes,
monitoreo en tiempo real mediante Grafana.

---

## Docker

Cada servicio corre en su propio contenedor Docker.

Para levantar todo el sistema:

docker compose up --build

Servicios principales:

Servicio	Puerto
orders-service	8000
catalog-service	8001
inventory-service	8002
notifications-service	8003
RabbitMQ	15672
Prometheus	9090
Grafana	3000

---

## Kubernetes

Se implementaron manifiestos Kubernetes para:

Deployments,
Services,
probes,
límites de recursos.

Características:

recreación automática de pods,
tolerancia a fallos,
escalabilidad,
comunicación DNS entre servicios.

---

## CI/CD

GitHub Actions automatiza:

instalación,
build,
ejecución de tests.

Workflow:

push automático,
ejecución de pytest,
validación continua del sistema.

---

## Tecnologías utilizadas
Python
FastAPI
gRPC
RabbitMQ
Redis
Prometheus
Grafana
Docker
Kubernetes
GitHub Actions
Locust
Pytest