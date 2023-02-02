from test_request_response_helpers import TestResponseBase
import json


class TestMetricResponseError(TestResponseBase):
    def test_responses(self):
        ctx = self._init_test()
        ctx.status_code = 200
        ctx.mocked_request = '{\
            "connectionDetails": {"url": "http://localhost:9000", "request_timeout_seconds": 15000},\
            "query":{\
                "conditions":[{"key":"__gauge__","value":{"value":"name","_type":"StringValue"},"_type":"EqualityCondition"}],\
                "startTime":1504400400000,\
                "endTime":1504411200000,\
                "metricField":"double",\
                "_type":"MetricsQuery"\
            },\
            "_type":"MetricsRequest"\
         }'

        ctx.url = "/api/metric"
        ctx.response_type = "tests/resources/MetricsResponseError"
        self.perform_test_responses(ctx)

    def _preprocess_request(self, mocked_request: str, mirror_response: str) -> str:
        if -1 != mirror_response.find("One of ['__gauge__'"):
            req = json.loads(mocked_request)
            req["query"]["conditions"] = []
            mocked_request = json.dumps(req)
        return mocked_request
