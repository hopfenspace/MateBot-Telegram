import urllib.parse
from typing import Optional

import requests


class APIConnector:
    def __init__(
            self,
            base_url: str,
            app_name: str = None,
            password: str = None,
            ca_path: str = None
    ):
        self.base_url = base_url + ("" if base_url.endswith("/") else "/")
        self.app_name = app_name
        self._password = password
        self._ca_path = ca_path
        self._session = requests.Session()
        if self._ca_path:
            self._session.verify = self._ca_path
        self._auth_token = None
        self._scope = ""
        self._client_id = ""
        self._client_secret = ""

        if self._password is not None:
            response = self.post(
                "/v1/login",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data="&".join([
                    "grant_type=password",
                    f"scope={urllib.parse.quote(self._scope)}",
                    f"username={urllib.parse.quote(self.app_name)}",
                    f"password={urllib.parse.quote(self._password)}",
                    f"client_id={urllib.parse.quote(self._client_id)}",
                    f"client_secret={urllib.parse.quote(self._client_secret)}"
                ])
            )

            if not response.ok:
                raise ValueError(
                    f"Logging in failed for username {self.app_name} (server "
                    f"{self.base_url!r}): response {response.status_code}"
                )

            content = response.json()
            if "token_type" not in content or "access_token" not in content or content["token_type"] != "bearer":
                raise ValueError(
                    f"Logging in failed for username {self.app_name} (server "
                    f"{self.base_url!r}): missing or invalid key(s) in response"
                )

            self.auth_token = content["access_token"]

    def __del__(self):
        self._session.close()

    def _fix_auth_header(self, kwargs) -> dict:
        if self.auth_token is None:
            return kwargs
        if "headers" in kwargs:
            kwargs["headers"].update({"Authorization": f"Bearer {self.auth_token}"})
        else:
            kwargs["headers"] = {"Authorization": f"Bearer {self.auth_token}"}
        return kwargs

    def status(self):
        return self.get("/v1/status")

    def get(self, endpoint: str, *args, **kwargs):
        return self._session.get(
            self.base_url + (endpoint[1:] if endpoint.startswith("/") else endpoint),
            *args,
            **self._fix_auth_header(kwargs)
        )

    def post(self, endpoint: str, *args, json_obj: Optional[dict] = None, **kwargs):
        return self._session.post(
            self.base_url + (endpoint[1:] if endpoint.startswith("/") else endpoint),
            *args,
            json=json_obj,
            **self._fix_auth_header(kwargs)
        )

    def put(self, endpoint: str, *args, json_obj: Optional[dict] = None, **kwargs):
        return self._session.put(
            self.base_url + (endpoint[1:] if endpoint.startswith("/") else endpoint),
            *args,
            json=json_obj,
            **self._fix_auth_header(kwargs)
        )

    def delete(self, endpoint: str, *args, json_obj: Optional[dict] = None, **kwargs):
        return self._session.delete(
            self.base_url + (endpoint[1:] if endpoint.startswith("/") else endpoint),
            *args,
            json=json_obj,
            **self._fix_auth_header(kwargs)
        )


connector = APIConnector("http://localhost:8000/")
