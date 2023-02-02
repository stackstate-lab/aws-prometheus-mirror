from test_request_response_helpers import TestRequestBase


class TestFieldValuesRequest(TestRequestBase):
    def test_requests(self):
        ctx = self._init_test()
        ctx.status_code = 200
        ctx.mocked_response = {"data": []}
        ctx.url = "/api/field/value"
        ctx.request_type = "tests/resources/FieldValuesRequest"
        self.perform_test_requests(ctx)
