from test_request_response_helpers import TestResponseBase


class TestFieldValuesResponse(TestResponseBase):
    def test_responses(self):
        ctx = self._init_test()
        ctx.status_code = 200
        ctx.mocked_request = '{\
            "connectionDetails": { "url": "http://localhost:9000", "request_timeout_seconds": 15000 },\
            "query":{\
                "conditions":[],\
                "field":{"fieldName":"label1","fieldType":"STRING","classified":false,"_type":"FieldDescriptor"},\
                "startTime":0,\
                "endTime":0,\
                "limit":2147483647,\
                "offset":0,\
                "latestFirst":true,\
                "_type":"FieldValuesQuery"},\
            "_type":"FieldValuesRequest"}'

        ctx.url = "/api/field/value"
        ctx.response_type = "tests/resources/FieldValuesResponse"
        self.perform_test_responses(ctx)
