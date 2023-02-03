import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from botocore.credentials import Credentials

from prometheus_mirror.model import (
    AwsConnectionDetails,
    Condition,
    ConditionValue,
    ConnectionDetails,
)

logger = logging.getLogger(__name__)

NAN_AS_ZERO = "ZERO"
NAN_AS_NONE = "NONE"

DEFAULT_BOTO3_RETRIES_COUNT = 50

DEFAULT_BOTO3_CONFIG = Config(
    retries=dict(
        max_attempts=DEFAULT_BOTO3_RETRIES_COUNT,
    )
)


class TooManyMetricsException(Exception):
    def __init__(self, fields):  # pylint: disable=super-init-not-called
        self.fields = fields


class PrometheusException(Exception):
    def __init__(self, error):  # pylint: disable=super-init-not-called
        self.error = error


class RequiredFieldException(Exception):
    pass


class InvalidPrometheusDataException(Exception):
    pass


class MetricNotFoundException(Exception):
    def __init__(self, query):  # pylint: disable=super-init-not-called
        self.query = query


class PrometheusClient:
    INSTANCES: Dict[str, "PrometheusClient"] = {}

    def __init__(self, config: ConnectionDetails):
        self.connection_details = config
        self.service_name = "aps"
        self.url = config.url if not config.url.endswith("/") else config.url[:-1]
        self.credentials = None
        self.region = None
        if config.aws:
            self.credentials = self._init_credentials(config.aws)
            self.region = config.aws.region_name
        self.nan_interpretation = config.nan_interpretation

    @staticmethod
    def get_instance(config: ConnectionDetails):
        instance = PrometheusClient.INSTANCES.get(config.url, None)
        if instance is None:
            instance = PrometheusClient(config)
            PrometheusClient.INSTANCES[config.url] = instance
        return instance

    def test_connection(self):
        health_uri = "api/v1/labels" if self.credentials else "-/healthy"
        response = self._do_get(health_uri)
        return response.status_code, response.text

    def list_labels(self, limit: int) -> Tuple[bool, List[str]]:
        labels_uri = "api/v1/labels"
        response = self._handle_failed_call(self._do_get(labels_uri))
        result = response.json()["data"]
        is_partial = limit < len(result)
        end = limit if limit < len(result) else len(result)
        return is_partial, result[0:end]

    def list_label_values(self, label: str, prefix: str, offset: int, max_result: int) -> Tuple[bool, List[str]]:
        values_uri = f"api/v1/label/{label}/values"
        response = self._handle_failed_call(self._do_get(values_uri))
        data = response.json()["data"]
        if prefix is not None:
            result = [value for value in data if value.startswith(prefix)]
        else:
            result = [value for value in data]

        start = offset if offset <= len(result) else len(result) - 1
        is_partial = start + max_result < len(result)
        end = start + max_result if start + max_result < len(result) else len(result)
        return is_partial, result[start:end]

    def get_series_values_in_range(
        self,
        conditions: Sequence[Condition],
        start: int,
        end: int,
        aggregation_method: Optional[str] = None,
        window: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        query = PrometheusQuery(conditions, aggregation_method, window)
        query_str = query.to_prometheus()

        query_uri = "api/v1/query_range"
        if window is None:
            window = 30  # default bucket size is 30 seconds

        response = self._handle_failed_call(
            self._do_get(query_uri, params={"query": query_str, "start": start, "end": end, "step": int(window)})
        )
        data = response.json()
        self._validate_metric_data(query_str, data)

        if limit is not None:
            return data["data"]["result"][0]["values"][:limit]
        else:
            return data["data"]["result"][0]["values"]

    def _validate_metric_data(self, query, data: Dict[str, Any]):
        if "status" in data and data["status"] == "error":
            raise PrometheusException(str(data))

        if "data" not in data or "result" not in data["data"]:
            raise InvalidPrometheusDataException(str(data))

        if len(data["data"]["result"]) > 1:
            fields = self._compute_differentiating_fields(data["data"]["result"])
            raise TooManyMetricsException(fields)

        if len(data["data"]["result"]) == 0:
            raise MetricNotFoundException(query)

    @staticmethod
    def _compute_differentiating_fields(series: Sequence[Dict[str, Any]]):
        values_for_key: Dict = defaultdict(set)
        for serie in series:
            for field in serie["metric"].keys():
                values_for_key[field] |= {serie["metric"][field]}

        res = []
        for key in values_for_key.keys():
            if len(values_for_key[key]) > 1:
                res.append(key)

        return res

    def _do_get(self, resource_uri: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        if params is None:
            params = {}
        uri = f"{self.url}/{resource_uri}"
        if self.credentials:
            response = self._signed_request(uri, method="GET", params=params)
        else:
            response = requests.get(url=uri, params=params)
        return response

    @staticmethod
    def _init_credentials(aws: AwsConnectionDetails) -> Optional[Credentials]:
        if aws is None:
            return None
        if aws.aws_secret_access_key and aws.aws_access_key_id and aws.aws_session_token:
            session = boto3.Session(
                aws_access_key_id=aws.aws_access_key_id,
                aws_secret_access_key=aws.aws_secret_access_key,
                aws_session_token=aws.aws_session_token,
            )
            return session.get_credentials().get_frozen_credentials()
        if aws.aws_secret_access_key and aws.aws_access_key_id:
            sts_client = boto3.client(
                "sts",
                config=DEFAULT_BOTO3_CONFIG,
                aws_access_key_id=aws.aws_access_key_id,
                aws_secret_access_key=aws.aws_secret_access_key,
            )
        else:
            sts_client = boto3.client("sts")
        assumed_role_object = sts_client.assume_role(
            RoleArn=aws.role_arn,
            RoleSessionName=aws.role_session_name,
            ExternalId=aws.external_id,
        )
        return assumed_role_object["Credentials"]

    def _signed_request(
        self,
        url: str,
        method: str = "POST",
        data: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        request = AWSRequest(method=method, url=url, data=data, params=params, headers=headers)
        SigV4Auth(self.credentials, self.service_name, self.region).add_auth(request)
        try:
            return requests.request(method=method, url=url, headers=dict(request.headers), data=data, params=params)
        except Exception as e:
            raise e

    @staticmethod
    def _handle_failed_call(response: requests.Response) -> requests.Response:
        if not response.ok:
            msg = "Failed to call [%s] . Status code %s" % (
                response.url,
                response.status_code,
            )
            logging.error(msg)
            logging.error("Response: %s" % response.text)
            raise Exception(f"{msg}. {response.text}")
        return response


class PrometheusQuery:
    def __init__(self, conditions: Sequence[Condition], aggregation_method: Optional[str], window: Optional[int]):
        self.conditions = conditions
        self.aggregation_method = aggregation_method
        self.window = window
        self.default_discretion_interval_seconds = "60"

    def to_prometheus(self) -> str:
        request_type, name, conditions = self.extract_parameters_from_conditions(self.conditions)
        if request_type == "__gauge__":
            query = name + self.conditions_list_to_query(conditions)
            if self.aggregation_method is not None:
                translated_aggregation = self.gauge_aggregation(self.aggregation_method, self.window)
                if translated_aggregation:
                    query = translated_aggregation[0] + query + translated_aggregation[1] + ")"
            return query
        elif request_type == "__counter__":
            query = name + self.conditions_list_to_query(conditions)
            if self.aggregation_method is not None:
                # quantile_over_time(0.5,increase(process_cpu_seconds_total{job="sockshop/catalog"}[12h])[12h:1m])
                translated_aggregation = self.counter_aggregation(self.aggregation_method, self.window)
                if translated_aggregation:
                    query = translated_aggregation[0] + query + translated_aggregation[1] + ")"
            else:
                query = "increase(" + query + "[" + str(self.default_discretion_interval_seconds) + "s])"
            return query
        else:  # ~tilda query
            return name

    @staticmethod
    def extract_parameters_from_conditions(condition_list: Sequence[Condition]) -> Tuple[str, str, Sequence[Condition]]:
        reserved_types = ["__gauge__", "__counter__", "~"]
        query_element = [
            (condition.key, condition.value.value) for condition in condition_list if condition.key in reserved_types
        ]
        conditions = [condition for condition in condition_list if condition.key not in reserved_types]
        if len(query_element) > 1:
            raise RequiredFieldException(f"Multiple values for {reserved_types}")
        if len(query_element) == 0:
            raise RequiredFieldException(f"One of {reserved_types} is required")
        return query_element[0][0], query_element[0][1], conditions

    def counter_aggregation(self, sts_aggregation: str, window: Optional[int]) -> Optional[Tuple[str, str]]:
        window_str = "" if window is None else str(int(window))
        # TO DO step greater then window
        full_window = "[" + window_str + "s])[" + window_str + "s:" + self.default_discretion_interval_seconds + "s]"
        return {
            None: None,
            "mean": ("avg_over_time(increase(", full_window),
            "percentile_25": ("quantile_over_time(0.25,increase(", full_window),
            "percentile_50": ("quantile_over_time(0.50,increase(", full_window),
            "percentile_75": ("quantile_over_time(0.75,increase(", full_window),
            "percentile_90": ("quantile_over_time(0.90,increase(", full_window),
            "percentile_95": ("quantile_over_time(0.95,increase(", full_window),
            "percentile_98": ("quantile_over_time(0.98,increase(", full_window),
            "percentile_99": ("quantile_over_time(0.99,increase(", full_window),
            "max": ("max_over_time(increase(", full_window),
            "min": ("min_over_time(increase(", full_window),
            "sum": ("sum_over_time(increase(", full_window),
            "event_count": ("count_over_time(increase(", full_window),
        }[sts_aggregation]

    @staticmethod
    def gauge_aggregation(sts_aggregation: str, window: Optional[int]) -> Optional[Tuple[str, str]]:
        return {
            None: None,
            "mean": ("avg(", ""),
            "percentile_25": ("quantile(0.25,", ""),
            "percentile_50": ("quantile(0.50,", ""),
            "percentile_75": ("quantile(0.75,", ""),
            "percentile_90": ("quantile(0.90,", ""),
            "percentile_95": ("quantile(0.95,", ""),
            "percentile_98": ("quantile(0.98,", ""),
            "percentile_99": ("quantile(0.99,", ""),
            "max": ("max(", ""),
            "min": ("min(", ""),
            "sum": ("sum(", ""),
            "event_count": ("count_over_time(", "[" + ("" if window is None else str(int(window))) + "s]"),
        }[sts_aggregation]

    def conditions_list_to_query(self, conditions: Sequence[Condition]) -> str:
        joined_conditions = ", ".join([self.condition_to_query(condition) for condition in conditions])
        return "{" + joined_conditions + "}"

    def condition_to_query(self, condition: Condition) -> str:
        return condition.key + "=" + self._value_to_prometheus(condition.value)

    def _value_to_prometheus(self, value: ConditionValue) -> str:
        raw_value = value.value
        descriptor = value.type_descriptor
        if descriptor == "InSetValue":
            or_regexp = "|".join(["(" + self.escape_regexp_token(str(item)) + ")" for item in sorted(raw_value)])
            return f'~"{or_regexp}"'
        if descriptor == "StringValue":
            return f'"{raw_value}"'
        elif descriptor == "BooleanValue":
            return f'"{str(raw_value).lower()}"'
        else:
            return f'"{str(raw_value)}"'

    @staticmethod
    def escape_regexp_token(token: str) -> str:
        metacharacters = "*+?()|"
        for c in metacharacters:
            token = token.replace(c, f"\\\\{c}")
        return token
