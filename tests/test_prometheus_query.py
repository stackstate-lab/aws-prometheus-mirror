import pytest
from typing import Any, Sequence, Tuple
from prometheus_mirror.prometheus import PrometheusQuery, RequiredFieldException
from prometheus_mirror.model import Condition, ConditionValue


class TestPrometheusQuery:
    def test_unspecified_query(self):
        query = PrometheusQuery(
            self._make_conditions([("string", "stringValue2"), ("double", 2.0), ("boolean", True)]),
            aggregation_method="mean",
            window=1000,
        )
        with pytest.raises(RequiredFieldException):
            query.to_prometheus()

    def test_gauge_query(self):
        query = PrometheusQuery(
            self._make_conditions(
                [("__gauge__", "mygauge"), ("string", "stringValue2"), ("double", 2.0), ("boolean", True)]
            ),
            aggregation_method="mean",
            window=1000,
        )
        assert 'avg(mygauge{string="stringValue2", double="2.0", boolean="true"})' == query.to_prometheus()

        query = PrometheusQuery(
            self._make_conditions(
                [("__gauge__", "mygauge"), ("string", "stringValue2"), ("double", 2.0), ("boolean", True)]
            ),
            aggregation_method=None,
            window=1,
        )
        assert 'mygauge{string="stringValue2", double="2.0", boolean="true"}' == query.to_prometheus()

    def test_counter_query(self):
        query = PrometheusQuery(
            self._make_conditions(
                [("__counter__", "mygauge"), ("string", "stringValue2"), ("double", 2.0), ("boolean", True)]
            ),
            aggregation_method="mean",
            window=1000,
        )
        assert (
            'avg_over_time(increase(mygauge{string="stringValue2",'
            ' double="2.0", boolean="true"}[1000s])[1000s:60s])' == query.to_prometheus()
        )

        query = PrometheusQuery(
            self._make_conditions(
                [("__counter__", "mygauge"), ("string", "stringValue2"), ("double", 2.0), ("boolean", True)]
            ),
            aggregation_method=None,
            window=1,
        )
        assert 'increase(mygauge{string="stringValue2", double="2.0", boolean="true"}[60s])' == query.to_prometheus()

    def test_tilda_query(self):
        query = PrometheusQuery(
            self._make_conditions(
                [
                    (
                        "~",
                        (
                            'histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket{name="orders"}[1m])) '
                            "by (name, le))"
                        ),
                    )
                ]
            ),
            aggregation_method="mean",
            window=1000,
        )
        assert (
            'histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket{name="orders"}[1m])) '
            "by (name, le))" == query.to_prometheus()
        )

        query = PrometheusQuery(
            self._make_conditions(
                [
                    (
                        "~",
                        'histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket{name="orders"}[1m]))'
                        " by (name, le))",
                    )
                ]
            ),
            aggregation_method=None,
            window=1,
        )
        assert (
            'histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket{name="orders"}[1m])) '
            "by (name, le))" == query.to_prometheus()
        )

    def test_set_condition(self):
        query = PrometheusQuery(
            self._make_conditions([("__counter__", "mygauge"), ("set", {"A", "B", ".*+?()|\\$^"})]),
            aggregation_method="mean",
            window=1000,
        )
        assert (
            'avg_over_time(increase(mygauge{set=~"(.\\\\*\\\\+\\\\?\\\\(\\\\)\\\\|\\$^)|(A)|(B)"}'
            "[1000s])[1000s:60s])"
        ) == query.to_prometheus()

    def _make_conditions(self, condition_input: Sequence[Tuple[str, Any]]) -> Sequence[Condition]:
        conditions = []
        for key, value in condition_input:
            conditions.append(self._to_condition(key, value))
        return conditions

    def _to_condition(self, key: str, value: Any) -> Condition:
        if isinstance(value, str):
            return self._make_string_condition(key, value)
        elif isinstance(value, bool):
            return self._make_boolean_condition(key, value)
        elif isinstance(value, (int, float, complex)):
            return self._make_double_condition(key, value)
        elif isinstance(value, set):
            return self._make_in_condition(key, value)
        raise AssertionError(f"Unknown value type {value}")

    @staticmethod
    def _make_string_condition(key: str, value: Any) -> Condition:
        return Condition(key=key, value=ConditionValue(value=value, _type="StringValue"), _type="EqualityCondition")

    @staticmethod
    def _make_boolean_condition(key: str, value: Any) -> Condition:
        return Condition(
            key=key, value=ConditionValue(value=str(value).lower(), _type="BooleanValue"), _type="EqualityCondition"
        )

    @staticmethod
    def _make_double_condition(key: str, value: Any) -> Condition:
        return Condition(key=key, value=ConditionValue(value=value, _type="DoubleValue"), _type="EqualityCondition")

    @staticmethod
    def _make_in_condition(key: str, value: Any) -> Condition:
        return Condition(key=key, value=ConditionValue(value=value, _type="InSetValue"), _type="EqualityCondition")
