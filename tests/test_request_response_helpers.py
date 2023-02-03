import json
from os import listdir
from os.path import isfile, join
import requests_mock
from fastapi.testclient import TestClient
from prometheus_mirror.mirror import app


class Context:
    def __init__(self):
        self.app = None
        self.inbound_ext = "mirror.json"
        self.outbound_ext = "prometheus.txt"
        self._default_headers = []
        self.maxDiff = None
        self.url = None
        self.request_type = None
        self.response_type = None
        self.status_code = 500
        self.mocked_response = None
        self.mocked_request = None


class TestRequestResponseBase:
    @staticmethod
    def _init_test():
        ctx = Context()
        ctx.app = TestClient(app)
        return ctx

    def _decompose_prometheus(self, request):
        url = self._get_string(request, "url")
        params = self._get_json(request, "params")
        timeout = self._get_int(request, "timeout")
        body_as_json = self._get_bool(request, "body_as_json")
        return url, params, timeout, body_as_json

    def _get_int(self, request, field):
        result = self._get_string(request, field)
        return int(result)

    def _get_json(self, request, field):
        result = self._get_string(request, field)
        return None if len(result) == 0 else self._load_json_or_text(result)

    def _get_bool(self, request, field):
        result = self._get_string(request, field)
        return True if result is None else result == "True"

    @staticmethod
    def _get_string(request, field):
        result = None
        for line in request.split("\n"):
            if line.startswith(field):
                result = line.replace(f"{field}:", "").strip()
                break
        return result

    @staticmethod
    def _load_json_or_text(line):
        try:
            return json.loads(line)
        except Exception:
            return line

    @staticmethod
    def _load(file_name):
        with open(file_name, "r") as file:
            return file.read()


class TestRequestBase(TestRequestResponseBase):
    def perform_test_requests(self, ctx):
        inbound_requests = [
            join(ctx.request_type, f)
            for f in listdir(ctx.request_type)
            if isfile(join(ctx.request_type, f)) and f.endswith(ctx.inbound_ext)
        ]
        for inbound_request_name in inbound_requests:
            inbound_str = self._load(inbound_request_name)
            outbound_str = self._load(inbound_request_name.replace(ctx.inbound_ext, ctx.outbound_ext))
            try:
                self._request(inbound_str, outbound_str, ctx)
            except Exception as e:
                print(f"Issue with request: {inbound_request_name}")
                raise e

    def _request(self, mirror_request: str, prometheus_request: str, ctx: Context):
        with requests_mock.Mocker(real_http=False) as m:
            url, params, timeout, body_as_json = self._decompose_prometheus(prometheus_request)
            adapter = m.register_uri(method="GET", url=url, json=ctx.mocked_response, status_code=ctx.status_code)
            response = ctx.app.post(url=ctx.url, json=json.loads(mirror_request))
            if response.status_code != ctx.status_code:
                print(json.dumps(response.json(), indent=4))
                assert response.status_code == ctx.status_code
            assert adapter.call_count == 1, f"Expected endpoint {url} to be called once. But was {adapter.call_count}"
            assert adapter.called


class TestResponseBase(TestRequestResponseBase):
    def perform_test_responses(self, ctx: Context):
        inbound_requests = [
            join(ctx.response_type, f)
            for f in listdir(ctx.response_type)
            if isfile(join(ctx.response_type, f)) and f.endswith(ctx.inbound_ext)
        ]
        for inbound_request_name in inbound_requests:
            inbound_str = self._load(inbound_request_name)
            outbound_file_name = inbound_request_name.replace(ctx.inbound_ext, ctx.outbound_ext)
            outbound_str = self._load(outbound_file_name)
            try:
                self._response(inbound_str, outbound_str, ctx)
            except Exception as e:
                print(f"Issue with response: {inbound_request_name}")
                raise e

    def _response(self, mirror_response: str, prometheus_response: str, ctx: Context):
        with requests_mock.Mocker(real_http=False) as m:
            url, body, status_code = self._response_decompose_prometheus(prometheus_response)
            mocked_request = self._preprocess_request(ctx.mocked_request, mirror_response)
            m.register_uri(method="GET", url=url, json=body, status_code=ctx.status_code)
            response = ctx.app.post(url=ctx.url, json=json.loads(mocked_request))
        if response.status_code != status_code:
            print(json.dumps(response.json(), indent=4))
            assert response.status_code == status_code
        assert response.json() == json.loads(mirror_response)

    def _response_decompose_prometheus(self, request):
        url = self._get_string(request, "url")
        body = self._get_json(request, "body")
        status_code = self._get_int(request, "status")
        return url, body, status_code

    def _preprocess_request(self, mocked_request: str, mirror_response: str) -> str:
        return mocked_request
