from test_request_response_helpers import TestResponseBase


class TestFieldNamesResponse(TestResponseBase):
    def test_responses(self):
        ctx = self._init_test()
        ctx.status_code = 200
        ctx.mocked_request = '{\
            "connectionDetails": { "url": "http://localhost:9000" },\
            "requestTimeout": 0,\
            "query": {\
                "conditions": [],\
                "startTime": 0,\
                "endTime": 0,\
                "limit": 1000,\
                "latestFirst": true,\
                "_type": "FieldNamesQuery"\
            },\
            "_type": "FieldNamesRequest"}'

        ctx.url = "/api/field/name"
        ctx.response_type = "tests/resources/FieldNamesResponse"
        self.perform_test_responses(ctx)
