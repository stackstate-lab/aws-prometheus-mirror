from test_request_response_helpers import TestRequestBase


class TestMetricRequest(TestRequestBase):
    def test_requests(self):
        ctx = self._init_test()
        ctx.status_code = 200
        ctx.mocked_response = {"data": {"result": [{"values": [[1, 1.0]]}]}}
        ctx.url = "/api/metric"
        ctx.request_type = "tests/resources/MetricsRequest"
        self.perform_test_requests(ctx)
