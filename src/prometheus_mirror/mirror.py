import logging
import traceback
from typing import List

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from prometheus_mirror.metric_request import MetricRequest
from prometheus_mirror.model import (
    FieldDescriptor,
    FieldNameResponse,
    FieldValuesResponse,
    MirrorRequest,
    RemoteMirrorError,
    Settings,
    TestConnectionRequest,
    TestConnectionResponse,
    ValueDescriptor,
)
from prometheus_mirror.prometheus import PrometheusClient

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

settings = Settings()
app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(
            RemoteMirrorError(
                summary="Request validation errors.",
                details=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
            )
        ),
    )


@app.middleware("http")
async def add_api_key_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-MIRROR-API-KEY"] = settings.API_KEY
    return response


@app.middleware("http")
async def handle_uncaught_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        traceback_info = traceback.format_exc().split("\n")
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                RemoteMirrorError(
                    summary="Internal server error.", details={"message": str(e), "trace": traceback_info}
                )
            ),
        )


@app.get("/")
async def root():
    return {"app": "StackState Prometheus Mirror"}


@app.post("/api/connection")
async def check_connection(request: TestConnectionRequest):
    client = PrometheusClient.get_instance(request.connection_details)
    status_code, details = client.test_connection()
    if status_code == 200:
        return TestConnectionResponse()
    else:
        return JSONResponse(
            status_code=status_code,
            content=jsonable_encoder(TestConnectionResponse(error={"details": details}, status="FAILURE")),
        )


@app.post("/api/metric")
async def fetch_metric(request: MirrorRequest):
    return MetricRequest(request).fetch_metric()


@app.post("/api/field/value")
async def fetch_field_value(request: MirrorRequest):
    query = request.query
    client = PrometheusClient.get_instance(request.connection_details)
    if not query.field:  # done because of mypy and the optional type
        raise Exception("Field name required")
    field_name = query.field.field_name
    if field_name in ["__counter__", "__gauge__"]:
        field_name = "__name__"
    is_partial, values = client.list_label_values(field_name, query.prefix, query.offset, query.limit)
    results: List[ValueDescriptor] = []
    for value in values:
        results.append(ValueDescriptor(value=value))
    field_response = FieldValuesResponse(values=results, is_partial=is_partial)
    return field_response


@app.post("/api/field/name")
async def fetch_field_name(request: MirrorRequest):
    field_response = FieldNameResponse()
    field_names = ["__counter__", "__gauge__", "~"]
    client = PrometheusClient.get_instance(request.connection_details)
    is_partial, labels = client.list_labels(request.query.limit)
    field_names.extend(labels)
    for field_name in field_names:
        field_response.fields.append(FieldDescriptor(fieldName=field_name))
    field_response.is_partial = is_partial
    return field_response


if __name__ == "__main__":
    uvicorn.run(
        "prometheus_mirror.mirror:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS,
    )
