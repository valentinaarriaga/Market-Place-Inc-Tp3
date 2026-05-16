import asyncio
import time

import grpc
import redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

import inventory_pb2
import inventory_pb2_grpc


app = FastAPI(title="Inventory Service")

# =========================
# Redis
# =========================
r = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    socket_timeout=2,
    socket_connect_timeout=2,
)

# =========================
# Stock original para gRPC
# =========================
stock = {
    1: 10,
    2: 30,
    3: 15,
}

# =========================
# Métricas Prometheus
# =========================
reserve_attempts_total = Counter(
    "reserve_attempts_total", "Cantidad total de intentos de reserva"
)

reserve_duration_seconds = Histogram(
    "reserve_duration_seconds", "Duracion de reservas en segundos"
)

overselling_attempts_total = Counter(
    "overselling_attempts_total", "Cantidad de intentos de overselling"
)

inventory_stock_level = Gauge(
    "inventory_stock_level", "Stock actual por producto", ["product_id"]
)


# =========================
# Schemas
# =========================
class ReserveRequest(BaseModel):
    product_id: str
    quantity: int


class ResetStockRequest(BaseModel):
    product_id: str
    stock: int


# =========================
# gRPC Service
# =========================
class InventoryService(inventory_pb2_grpc.InventoryServiceServicer):
    async def ReserveStock(self, request, context):
        product_id = request.product_id
        quantity = request.quantity

        if product_id not in stock:
            return inventory_pb2.ReserveStockResponse(
                success=False, message="Producto inexistente"
            )

        if stock[product_id] < quantity:
            return inventory_pb2.ReserveStockResponse(
                success=False, message="Stock insuficiente"
            )

        stock[product_id] -= quantity

        return inventory_pb2.ReserveStockResponse(
            success=True,
            message=f"Stock reservado. Stock restante: {stock[product_id]}",
        )


async def start_grpc_server():
    server = grpc.aio.server()
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(
        InventoryService(), server
    )
    server.add_insecure_port("[::]:50051")
    await server.start()
    await server.wait_for_termination()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_grpc_server())

    # Stock inicial para Redis usado por /reserve
    try:
        if r.get("stock:iphone") is None:
            r.set("stock:iphone", 10)
        inventory_stock_level.labels(product_id="iphone").set(
            int(r.get("stock:iphone") or 0)
        )
    except redis.exceptions.RedisError:
        print("Redis no disponible al iniciar. Se intentara usar luego.")


# =========================
# Endpoints base
# =========================
@app.get("/health")
def health():
    return {"status": "ok", "service": "inventory"}


@app.get("/stock")
def get_stock():
    try:
        keys = r.keys("stock:*")
        if keys:
            result = {}
            for key in keys:
                product_id = key.replace("stock:", "")
                result[product_id] = int(r.get(key))
            return result
    except redis.exceptions.RedisError:
        pass

    return stock


# =========================
# Endpoint nuevo TP Final
# =========================
@app.post("/reserve")
def reserve(req: ReserveRequest):
    start = time.time()
    reserve_attempts_total.inc()

    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")

    lock_key = f"lock:{req.product_id}"
    stock_key = f"stock:{req.product_id}"

    try:
        lock = r.set(lock_key, "reserved", nx=True, ex=5)

        if not lock:
            raise HTTPException(
                status_code=503,
                detail="Otro usuario esta comprando este producto. Reintenta.",
            )

        try:
            current_stock = int(r.get(stock_key) or 0)

            if current_stock < req.quantity:
                raise HTTPException(status_code=400, detail="Sin stock suficiente")

            new_stock = current_stock - req.quantity

            if new_stock < 0:
                overselling_attempts_total.inc()
                raise HTTPException(
                    status_code=500, detail="Error critico: overselling detectado"
                )

            r.set(stock_key, new_stock)
            inventory_stock_level.labels(product_id=req.product_id).set(new_stock)

            return {
                "status": "reserved",
                "product_id": req.product_id,
                "quantity": req.quantity,
                "stock_remaining": new_stock,
            }

        finally:
            r.delete(lock_key)

    except redis.exceptions.RedisError:
        raise HTTPException(
            status_code=503, detail="Redis no disponible. Intente nuevamente."
        )

    finally:
        reserve_duration_seconds.observe(time.time() - start)


@app.post("/reset-stock")
def reset_stock(req: ResetStockRequest):
    if req.stock < 0:
        raise HTTPException(status_code=400, detail="El stock no puede ser negativo")

    r.set(f"stock:{req.product_id}", req.stock)
    r.delete(f"lock:{req.product_id}")

    inventory_stock_level.labels(product_id=req.product_id).set(req.stock)

    return {"status": "ok", "product_id": req.product_id, "stock": req.stock}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
