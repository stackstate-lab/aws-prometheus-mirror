import logging
from typing import Any, Optional, Sequence, Tuple

from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from prometheus_mirror.model import (
    AggregatedMetricTelemetryResponse,
    MetricsNotFoundError,
    MetricsResponse,
    MirrorRequest,
    Query,
    RawMetricTelemetryResponse,
    RemoteMirrorError,
)
from prometheus_mirror.prometheus import (
    NAN_AS_ZERO,
    InvalidPrometheusDataException,
    MetricNotFoundException,
    PrometheusClient,
    PrometheusException,
    RequiredFieldException,
    TooManyMetricsException,
)

logger = logging.getLogger(__name__)


class MetricRequest:
    def __init__(self, request: MirrorRequest):
        self.request = request

    def fetch_metric(self) -> MetricsResponse | JSONResponse:
        query = self.request.query
        try:
            start_timestamp = int(query.start_time / 1000)
            end_timestamp_millis = query.end_time
            end_timestamp = int(end_timestamp_millis / 1000)

            aggregation = None
            window = 30000
            if query.aggregation:
                aggregation = query.aggregation.method.lower()
                window = query.aggregation.bucket_size_millis
                if window and int(window) < 30000:
                    window = 30000  # minimal bucket size 30 seconds
            window_seconds = window / 1000.0
            limit = query.limit
            client = PrometheusClient.get_instance(self.request.connection_details)
            nan_interpretation = client.nan_interpretation
            result = client.get_series_values_in_range(
                query.conditions,
                start_timestamp,
                end_timestamp,
                aggregation,
                window_seconds,
                limit,
            )
            metrics_response = self._make_metric_response(
                query, window, end_timestamp_millis, result, nan_interpretation
            )
            return metrics_response
        except InvalidPrometheusDataException as e:
            return self.error_response(self.generic_error("Invalid prometheus response.", f"{e}"))
        except MetricNotFoundException as e:
            return self.error_response(self.metric_not_found_error(f"{e.query}"))
        except RequiredFieldException as e:
            return self.error_response(self.metric_not_found_error(str(query), f"{str(e)}"))
        except TooManyMetricsException as e:
            return self.error_response(self.generic_error("Too many metrics.", f"{e}"))
        except PrometheusException as e:
            return self.error_response(self.generic_error("Prometheus error.", f"{e}"))
        except Exception as e:  # pylint: disable=broad-except
            return self.error_response(self.generic_error("Unexpected error.", f"{e}"))

    @staticmethod
    def _make_metric_response(
        query: Query,
        window: int,
        end_timestamp_millis: int,
        result: Sequence[Tuple[int, float]],
        nan_interpretation: str,
    ) -> MetricsResponse:
        if query.aggregation:
            return MetricRequest._make_agg_metric_response(
                end_timestamp_millis, nan_interpretation, result, int(window)
            )
        else:
            return MetricRequest._make_raw_metric_response(end_timestamp_millis, nan_interpretation, result)

    @staticmethod
    def _make_raw_metric_response(end_timestamp_millis, nan_interpretation, result):
        points = []
        for value in result:
            timestamp = value[0] * 1000
            value_str = value[1]
            if timestamp <= end_timestamp_millis:
                if str(value_str).lower() == "nan":
                    if nan_interpretation == NAN_AS_ZERO:
                        points.append([0.0, timestamp])
                    else:
                        logger.error(f"Skipping NaN value for timestampt: {value_str}.")
                else:
                    points.append([float(value_str), timestamp])
        response = MetricsResponse()
        response.telemetry = RawMetricTelemetryResponse(points=points)
        return response

    @staticmethod
    def _make_agg_metric_response(end_timestamp_millis, nan_interpretation, result, window):
        points = []
        for value in result:
            bucket_start = value[0] * 1000
            bucket_end = bucket_start + window
            value_str = value[1]
            if bucket_end <= end_timestamp_millis:
                if str(value_str).lower() == "nan":
                    if nan_interpretation == NAN_AS_ZERO:
                        points.append([0.0, bucket_start, bucket_end])
                    else:
                        logger.error(f"Skipping NaN value for timestampt: {value_str}.")
                else:
                    points.append([float(value_str), bucket_start, bucket_end])
        response = MetricsResponse()
        response.telemetry = AggregatedMetricTelemetryResponse(points=points)
        return response

    @staticmethod
    def generic_error(summary: Any, details: Optional[Any] = None) -> RemoteMirrorError:
        return RemoteMirrorError(summary=summary, details=details)

    @staticmethod
    def metric_not_found_error(metric: str, details: Optional[Any] = None) -> MetricsNotFoundError:
        return MetricsNotFoundError(metric=metric, details=details)

    @staticmethod
    def error_response(error: Any) -> JSONResponse:
        logger.error(f"Request error: {error}")
        return JSONResponse(status_code=500, content=jsonable_encoder(error))
