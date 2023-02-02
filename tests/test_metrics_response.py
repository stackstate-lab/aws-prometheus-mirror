from test_request_response_helpers import TestResponseBase
import json


class TestMetricSuccessResponse(TestResponseBase):
    def test_responses(self):
        ctx = self._init_test()
        ctx.status_code = 200
        ctx.mocked_request = '{\
            "connectionDetails": {"url": "http://localhost:9000", "request_timeout_seconds": 15000},\
            "requestTimeout":15000,\
            "query":{\
                "conditions":[{"key":"__gauge__","value":{"value":"name","_type":"StringValue"},"_type":"EqualityCondition"}],\
                "startTime":1555408501000,\
                "endTime":1555408711000,\
                "metricField":"double",\
                "_type":"MetricsQuery"\
            },\
            "_type":"MetricsRequest"\
         }'

        ctx.url = "/api/metric"
        ctx.response_type = "tests/resources/MetricsResponse"
        self.perform_test_responses(ctx)

    def _preprocess_request(self, mocked_request: str, mirror_response: str) -> str:
        if -1 != mirror_response.find("AggregatedMetricTelemetry"):
            req = json.loads(mocked_request)
            req["query"]["aggregation"] = {
                "method": "MEAN",
                "bucketSizeMillis": 10000,
                "_type": "Aggregation",
            }
            mocked_request = json.dumps(req)
        return mocked_request
