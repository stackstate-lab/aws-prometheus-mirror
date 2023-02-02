from test_request_response_helpers import TestRequestBase


class TestFieldNamesRequest(TestRequestBase):
    def test_requests(self):
        ctx = self._init_test()
        ctx.status_code = 200
        ctx.mocked_response = {"data": []}
        ctx.url = "/api/field/name"
        ctx.request_type = "tests/resources/FieldNamesRequest"
        self.perform_test_requests(ctx)
