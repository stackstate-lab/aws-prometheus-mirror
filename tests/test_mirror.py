from fastapi.testclient import TestClient
import os
from prometheus_mirror.mirror import app
import requests_mock
from dotenv import load_dotenv

load_dotenv()

client = TestClient(app)

connection_details = {
    "connectionDetails": {
        "url": os.getenv("prometheus_url"),
        "aws": {
            "aws_access_key_id": os.getenv("aws_access_key_id"),
            "aws_secret_access_key": os.getenv("aws_secret_access_key"),
            "aws_session_token": os.getenv("aws_session_token"),
        },
    }
}


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"app": "StackState Prometheus Mirror"}


def test_invalid_request_content():
    data = {}
    response = client.post("/api/connection", json=data)
    assert response.status_code == 500
    assert response.json() == {
        "_type": "RemoteMirrorError",
        "details": {
            "body": {},
            "detail": [{"loc": ["body", "connectionDetails"], "msg": "field required", "type": "value_error.missing"}],
        },
        "summary": "Request validation errors.",
    }


def test_connection_failure():
    data = {
        "connectionDetails": {
            "url": "https://aps-workspaces.eu-west-1.amazonaws.com/workspaces/ws-43e5c1ec/",
            "aws": {
                "aws_access_key_id": "ASIA2BOTXQ5Z6DLUEQ4M",
                "aws_secret_access_key": "LmiDSrmniaTsdvcxf+cRjCSbd3ggRfoQgw5Oeoey",
                "aws_session_token": "IQoJb3JpZ2luX2VjEEkaDGV1LWNlbnRyYWwtMSJHMEUCIFJUEWQT",
            },
        }
    }
    aws_response_data = {"message": "The security token included in the request is expired"}
    with requests_mock.Mocker() as m:
        m.register_uri(
            method="GET",
            url=f'{data["connectionDetails"]["url"]}api/v1/labels',
            json=aws_response_data,
            status_code=403,
        )
        response = client.post("/api/connection", json=data)
    assert response.status_code == 403
    expected_data = {
        "_type": "TestConnectionResponse",
        "error": {
            "_type": "MetricStoreConnectionError",
            "details": '{"message": "The security token included in the request ' 'is expired"}',
        },
        "status": "FAILURE",
    }
    assert response.json() == expected_data


def test_connection_success():
    data = connection_details
    aws_response_data = {"status": "success", "data": ["__name__", "cpu"]}
    with requests_mock.Mocker(real_http=False) as m:
        m.register_uri(
            method="GET",
            url=f'{data["connectionDetails"]["url"]}api/v1/labels',
            json=aws_response_data,
            status_code=200,
        )
        response = client.post("/api/connection", json=data)
    assert response.status_code == 200
    expected_data = {
        "_type": "TestConnectionResponse",
        "error": None,
        "status": "OK",
    }
    assert response.json() == expected_data
