from typing import Any, List, Optional

from pydantic import BaseModel, BaseSettings, Field


class AwsConnectionDetails(BaseModel):
    role_arn: Optional[str]
    external_id: Optional[str]
    aws_access_key_id: Optional[str]
    aws_secret_access_key: Optional[str]
    aws_session_token: Optional[str]
    region_name: str = Field(default="eu-west-1")
    role_session_name: str = Field(default="StackState-Prometheus-Mirror")


class ConnectionDetails(BaseModel):
    url: str
    request_timeout_seconds: int = Field(default=30)
    nan_interpretation: str = Field(default="ZERO")
    aws: Optional[AwsConnectionDetails]


class TestConnectionRequest(BaseModel):
    connection_details: ConnectionDetails = Field(alias="connectionDetails")
    _type: str


class ConditionValue(BaseModel):
    value: Any
    type_descriptor: str = Field(alias="_type")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self.type_descriptor = data.get("_type", "StringValue")


class Condition(BaseModel):
    key: str
    value: ConditionValue
    _type: str


class FieldDescriptor(BaseModel):
    type_descriptor: str = Field("FieldDescriptor", alias="_type")
    classified: bool = False
    field_type: str = Field("STRING", alias="fieldType")
    field_name: str = Field(None, alias="fieldName")


class Aggregation(BaseModel):
    method: str
    bucket_size_millis: int = Field(10000, alias="bucketSizeMillis")
    type_descriptor: str = Field("Aggregation", alias="_type")


class Query(BaseModel):
    conditions: List[Condition] = []
    field: Optional[FieldDescriptor] = None
    aggregation: Optional[Aggregation] = None
    metric_field: Optional[str] = Field("", alias="metricField")
    start_time: int = Field(0, alias="startTime")
    end_time: int = Field(0, alias="endTime")
    last_first: bool = Field(False, alias="lastFirst")
    prefix: Optional[str] = Field("", alias="fieldValuePrefix")
    limit: int = 1000
    offset: Optional[int] = 0
    type_descriptor: str = Field(None, alias="_type")


class MirrorRequest(BaseModel):
    connection_details: ConnectionDetails = Field(alias="connectionDetails")
    query: Query
    type_descriptor: str = Field("", alias="_type")


class FieldNameResponse(BaseModel):
    type_descriptor: str = Field("FieldNamesResponse", alias="_type")
    fields: List[FieldDescriptor] = []
    is_partial: bool = Field(False, alias="isPartial")


class ValueDescriptor(BaseModel):
    type_descriptor: str = Field("CompleteValue", alias="_type")
    value: str


class FieldValuesResponse(BaseModel):
    type_descriptor: str = Field("FieldValuesResponse", alias="_type")
    values: List[ValueDescriptor] = []
    is_partial: bool = Field(False, alias="isPartial")


class AggregatedMetricTelemetryResponse(BaseModel):
    type_descriptor: str = Field("AggregatedMetricTelemetry", alias="_type")
    points: List[List[Any]] = []
    data_format: List[str] = Field(["value", "startTimestamp", "endTimestamp"], alias="dataFormat")
    is_partial: bool = Field(False, alias="isPartial")


class RawMetricTelemetryResponse(BaseModel):
    type_descriptor: str = Field("RawMetricTelemetry", alias="_type")
    points: List[List[Any]] = []
    data_format: List[str] = Field(["value", "timestamp"], alias="dataFormat")
    is_partial: bool = Field(False, alias="isPartial")


class MetricsNotFoundError(BaseModel):
    type_descriptor: str = Field("MetricNotFoundError", alias="_type")
    metric: str
    details: Any


class RemoteMirrorError(BaseModel):
    type_descriptor: str = Field("RemoteMirrorError", alias="_type")
    summary: str
    details: Optional[Any]


class MetricsResponse(BaseModel):
    type_descriptor: str = Field("MetricsResponse", alias="_type")
    telemetry: AggregatedMetricTelemetryResponse | RawMetricTelemetryResponse = Field(None)


class TestConnectionError(BaseModel):
    type_descriptor: str = Field("MetricStoreConnectionError", alias="_type")
    details: str


class TestConnectionResponse(BaseModel):
    type_descriptor: str = Field("TestConnectionResponse", alias="_type")
    status: str = "OK"
    error: Optional[TestConnectionError]


class Settings(BaseSettings):
    API_KEY: str = "unsecure"
    RELOAD: bool = False
    PORT: int = 9090
    WORKERS: int = 6
