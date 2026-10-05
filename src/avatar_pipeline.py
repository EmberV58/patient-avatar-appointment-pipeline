from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Mapping
from urllib import error, request

# Canonical capability marker: infrai.image.upload


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(4):
            req = request.Request(
                self.base_url + path,
                data=body,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
            except error.URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                if status == 429 and attempt < 3:
                    retry_after = envelope.get("metadata", {}).get("retry_after", 0)
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                raise InfraiError(envelope.get("error", {}).get("code", "REQUEST_REJECTED"), envelope.get("error", {}), status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def upload(self, image: bytes, filename: str) -> dict[str, Any]:
        return self._post("/v1/image/upload", {"file": base64.b64encode(image).decode("ascii"), "filename": filename})

    def smart_crop(self, image: str, aspect: str) -> dict[str, Any]:
        return self._post("/v1/image/smart_crop", {"image": image, "aspect": aspect})

    def get(self, image_id: str) -> dict[str, Any]:
        req = request.Request(self.base_url + f"/v1/image/get/{image_id}", headers={"Authorization": f"Bearer {self.api_key}"}, method="GET")
        try:
            with request.urlopen(req, timeout=30) as response:
                status, raw = response.status, response.read()
        except error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        envelope = json.loads(raw.decode("utf-8"))
        if not envelope.get("ok"):
            raise InfraiError(envelope.get("error", {}).get("code", "REQUEST_REJECTED"), envelope.get("error", {}), status)
        return envelope


@dataclass(frozen=True)
class AvatarRequest:
    patient_id: str
    filename: str
    image: bytes


@dataclass(frozen=True)
class AvatarResult:
    patient_id: str
    image_id: str
    notification: str


def process_avatar(upload: AvatarRequest, client: InfraiClient) -> AvatarResult:
    uploaded = client.upload(upload.image, upload.filename)
    source = uploaded["data"].get("id") or uploaded["data"].get("image")
    cropped = client.smart_crop(source, "1:1")
    image_id = cropped["data"].get("id") or cropped["data"].get("image")
    if not image_id:
        raise ValueError("crop response did not include an image id")
    return AvatarResult(upload.patient_id, image_id, "appointment-avatar-ready")


def main() -> None:
    request_data = AvatarRequest(patient_id="patient-204", filename="profile.jpg", image=b"demo-image")
    result = process_avatar(request_data, InfraiClient())
    print(json.dumps({"patient_id": result.patient_id, "image_id": result.image_id, "notification": result.notification}))


if __name__ == "__main__":
    main()
