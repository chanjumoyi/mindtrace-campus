"""Exercise the Windows upload receiver with synthetic collection packages."""

from __future__ import annotations

import base64
import csv
import hashlib
import http.client
import json
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows HttpListener receiver")

RECEIVER_SCRIPT = Path(__file__).resolve().parents[1] / "upload-server.ps1"
TEST_TOKEN = "synthetic-test-token"
UPLOAD_PATH = "/api/handwriting-sessions"


@dataclass(frozen=True)
class Receiver:
    port: int
    upload_root: Path

    def request(
        self,
        method: str,
        path: str = UPLOAD_PATH,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("localhost", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def upload(
        self,
        body: bytes,
        *,
        filename: str = "synthetic-session.json",
        token: str | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        headers = {"Content-Type": "application/json; charset=utf-8", "X-Filename": filename}
        if token is not None:
            headers["X-Upload-Token"] = token
        return self.request("POST", body=body, headers=headers)


@contextmanager
def running_receiver(
    directory: Path, *, require_token: bool = False, extra_args: tuple[str, ...] = ()
) -> Iterator[Receiver]:
    powershell = shutil.which("powershell.exe")
    assert powershell, "Windows PowerShell is required to exercise the receiver"
    assert RECEIVER_SCRIPT.is_file(), f"Missing receiver: {RECEIVER_SCRIPT}"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    upload_root = directory / "uploads"
    receiver = Receiver(port, upload_root)
    command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(RECEIVER_SCRIPT),
        "-Prefix",
        f"http://localhost:{port}/",
        "-UploadRoot",
        str(upload_root),
        "-Token",
        TEST_TOKEN,
        "-MinFreeBytes",
        "0",
    ]
    if require_token:
        command.append("-RequireToken")
    command.extend(extra_args)
    output_path = directory / "receiver-output.log"
    with output_path.open("wb") as output:
        process = subprocess.Popen(
            command,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail(
                        f"Receiver exited with {process.returncode}: "
                        + output_path.read_text(encoding="utf-8", errors="replace")
                    )
                try:
                    status, _, _ = receiver.request("GET", "/health")
                    if status == 200:
                        break
                except (OSError, http.client.HTTPException):
                    pass
                time.sleep(0.05)
            else:
                pytest.fail(
                    "Receiver did not become ready: "
                    + output_path.read_text(encoding="utf-8", errors="replace")
                )
            yield receiver
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


@pytest.fixture(scope="module")
def receiver(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Receiver]:
    with running_receiver(tmp_path_factory.mktemp("collector-default")) as instance:
        yield instance


@pytest.fixture(scope="module")
def required_receiver(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Receiver]:
    with running_receiver(
        tmp_path_factory.mktemp("collector-required"), require_token=True
    ) as instance:
        yield instance


@pytest.fixture(scope="module")
def strict_image_receiver(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Receiver]:
    with running_receiver(
        tmp_path_factory.mktemp("collector-strict-image"),
        extra_args=("-RequireImageConsent",),
    ) as instance:
        yield instance


def synthetic_package(schema_version: str, session_id: str = "SYNTHETIC-SESSION") -> dict:
    who5 = schema_version in {"1.7.0", "1.8.0"}
    scores = [0, 1, 2, 4, 5] if who5 else [index % 5 for index in range(18)]
    item_prefix = "WHO5" if who5 else "MRS"
    return {
        "schemaVersion": schema_version,
        "appVersion": f"handwriting-collector-mobile/{schema_version}",
        "sessionId": session_id,
        "participantId": "SYNTHETIC-PARTICIPANT",
        "datasetEligibility": "eligible",
        "device": {"deviceProfileId": "SYNTHETIC-PROFILE"},
        "questionnaire": {
            "instrumentId": "WHO_5" if who5 else "MINDTRACE_RECENT_STATE_18",
            "responseSchemaVersion": "questionnaire-response/2.0.0"
            if who5
            else "questionnaire-response/1.2.0",
            "items": [
                {
                    "questionId": f"{item_prefix}_{index + 1:02d}",
                    "rawScore": score,
                    "scoredScore": score,
                }
                for index, score in enumerate(scores)
            ],
            "derived": {
                "rawTotal": sum(scores),
                "percentageScore": sum(scores) * 4 if who5 else None,
            },
        },
        "attempts": [
            {
                "taskId": "SYNTHETIC_WRITING",
                "taskTitle": "合成书写采集回归测试",
                "deviceProfileId": "SYNTHETIC-PROFILE",
                "tiltValid": False,
                "pressureDetected": False,
                "pressureValid": False,
                "metrics": {"pauseInStrokeMs": 0, "betweenStrokeMs": 0},
                "canvas": {"width": 360, "height": 400, "devicePixelRatio": 3},
                "points": [
                    {
                        "seq": 0,
                        "strokeId": 1,
                        "phase": "down",
                        "pointerType": "pen",
                        "x": 10.125,
                        "y": 20.75,
                        "xNorm": 0.028125,
                        "yNorm": 0.051875,
                        "elapsedMs": 0,
                        "taskElapsedMs": 120.5,
                        "timestamp": 1792897200000,
                        "eventTimestampMs": 1000.5,
                        "pressure": 0.375,
                        "width": 1,
                        "height": 1,
                        "insideCanvas": True,
                    }
                ],
            }
        ],
    }


def package_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def assert_stored(receiver: Receiver, response: bytes, original: bytes) -> Path:
    result = json.loads(response)
    assert result["ok"] is True
    assert result["bytes"] == len(original)
    assert isinstance(result["storedAs"], str)
    stored = (receiver.upload_root / result["storedAs"]).resolve()
    assert stored.is_relative_to(receiver.upload_root.resolve())
    assert stored.read_bytes() == original
    assert json.loads(stored.read_bytes()) == json.loads(original)
    return stored


PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGNgAAAAAgAB4iG8MwAAAABJRU5ErkJggg=="
)
PNG_BYTES = base64.b64decode(PNG_BASE64)


def image_package(
    schema_version: str = "1.7.0",
    session_id: str = "SYNTHETIC-IMAGE-SESSION",
    *,
    accepted: bool = True,
    consent_version: str = "local-anonymous-collection-v1.2",
    scopes: tuple[str, ...] = ("demographics", "research", "model_development"),
    mime_type: str = "image/png",
    data_url: str | None = None,
) -> dict:
    payload = synthetic_package(schema_version, session_id)
    payload["consent"] = {
        "status": "granted" if accepted else "not_granted",
        "accepted": accepted,
        "version": consent_version,
        "dataUseScope": list(scopes),
    }
    payload["attempts"][0]["image"] = {
        "filename": f"{session_id}-SYNTHETIC_WRITING-1.png",
        "mimeType": mime_type,
        "dataUrl": data_url or f"data:image/png;base64,{PNG_BASE64}",
    }
    return payload


def manifest_v2_rows(receiver: Receiver) -> list[dict[str, str]]:
    path = receiver.upload_root / "manifest-v2.csv"
    assert path.is_file(), "manifest-v2.csv was not written"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def image_index_rows(receiver: Receiver) -> list[dict[str, str]]:
    path = receiver.upload_root / "image-index.csv"
    assert path.is_file(), "image-index.csv was not written"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("schema_version", ["1.8.0", "1.7.0", "1.6.0"])
def test_default_accepts_current_and_legacy_packages_without_token(
    receiver: Receiver, schema_version: str
) -> None:
    body = package_bytes(synthetic_package(schema_version))
    status, _, response = receiver.upload(body, filename=f"synthetic-{schema_version}.json")
    assert status == 200, response
    assert_stored(receiver, response, body)


def test_no_image_package_uses_participant_date_session_folder(receiver: Receiver) -> None:
    body = package_bytes(synthetic_package("1.7.0", "SYNTHETIC-FOLDER"))
    status, _, response = receiver.upload(body, filename="synthetic-folder.json")
    assert status == 200, response
    stored = assert_stored(receiver, response, body)
    relative = stored.relative_to(receiver.upload_root)
    assert len(relative.parts) == 4
    assert relative.parts[0] == "SYNTHETIC-PARTICIPANT"
    assert relative.parts[1].count("-") == 2
    assert relative.parts[2] == "synthetic-folder"
    assert relative.parts[3] == "synthetic-folder.json"


def test_image_package_is_accepted_and_recorded_in_manifest_v2(receiver: Receiver) -> None:
    payload = image_package(session_id="SYNTHETIC-IMAGE-STORAGE")
    body = package_bytes(payload)
    status, _, response = receiver.upload(body, filename="synthetic-image.json")
    assert status == 200, response
    result = json.loads(response)
    assert result["images"] == 1
    assert result["imageBytes"] == len(PNG_BYTES)
    stored = assert_stored(receiver, response, body)
    image_files = sorted(stored.parent.glob("*.png"))
    assert len(image_files) == 1
    assert image_files[0].name == payload["attempts"][0]["image"]["filename"]
    assert image_files[0].parent == stored.parent
    assert image_files[0].read_bytes() == PNG_BYTES
    assert len(result["imageFiles"]) == 1
    assert result["imageFiles"][0].endswith(image_files[0].name)
    rows = manifest_v2_rows(receiver)
    row = next(item for item in rows if item["session_id"] == "SYNTHETIC-IMAGE-STORAGE")
    assert row["images"] == "1"
    assert row["image_bytes"] == str(len(PNG_BYTES))
    assert row["schema_version"] == "1.7.0"
    assert row["consent_version"] == "local-anonymous-collection-v1.2"
    assert row["consent_accepted"] == "True"
    index_rows = image_index_rows(receiver)
    index = next(item for item in index_rows if item["session_id"] == "SYNTHETIC-IMAGE-STORAGE")
    assert index["stored_as"] == result["storedAs"]
    assert index["image_file"].endswith(image_files[0].name)
    assert index["bytes"] == str(len(PNG_BYTES))
    assert index["sha256"].lower() == hashlib.sha256(PNG_BYTES).hexdigest()


def test_image_package_without_consent_is_rejected(receiver: Receiver) -> None:
    payload = image_package()
    payload.pop("consent")
    status, _, response = receiver.upload(
        package_bytes(payload), filename="synthetic-no-consent.json"
    )
    assert status == 422, response
    assert json.loads(response)["error"] == "consent_missing_or_not_granted"


def test_image_package_with_rejected_consent_is_rejected(receiver: Receiver) -> None:
    payload = image_package(accepted=False)
    status, _, response = receiver.upload(
        package_bytes(payload), filename="synthetic-rejected-consent.json"
    )
    assert status == 422, response
    assert json.loads(response)["error"] == "consent_missing_or_not_granted"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mime_type": "text/html"},
        {"data_url": "data:image/png;base64,!!!"},
        {"data_url": "data:image/png;base64,bm90IGEgcG5n"},
    ],
)
def test_invalid_image_payload_is_rejected(receiver: Receiver, kwargs: dict) -> None:
    status, _, response = receiver.upload(
        package_bytes(image_package(**kwargs)), filename="synthetic-invalid-image.json"
    )
    assert status == 422, response
    assert json.loads(response)["error"] == "invalid_image_payload"


def test_too_many_images_are_rejected(receiver: Receiver) -> None:
    payload = image_package()
    payload["attempts"] = [
        {
            "taskId": f"SYNTHETIC_{index}",
            "points": [],
            "image": {
                "filename": f"image-{index}.png",
                "mimeType": "image/png",
                "dataUrl": f"data:image/png;base64,{PNG_BASE64}",
            },
        }
        for index in range(13)
    ]
    status, _, response = receiver.upload(
        package_bytes(payload), filename="synthetic-too-many.json"
    )
    assert status == 413, response
    assert json.loads(response)["error"] == "too_many_images"


def test_strict_image_consent_rejects_legacy_version(strict_image_receiver: Receiver) -> None:
    status, _, response = strict_image_receiver.upload(
        package_bytes(image_package()), filename="synthetic-legacy-consent.json"
    )
    assert status == 422, response
    assert json.loads(response)["error"] == "consent_version_too_old"


def test_strict_image_consent_accepts_current_scope(strict_image_receiver: Receiver) -> None:
    payload = image_package(
        consent_version="trajectory-upload-collection-v1.3",
        scopes=("demographics", "research", "model_development", "server_storage"),
    )
    body = package_bytes(payload)
    status, _, response = strict_image_receiver.upload(body, filename="synthetic-strict-image.json")
    assert status == 200, response
    assert_stored(strict_image_receiver, response, body)


def test_same_filename_keeps_both_original_packages(receiver: Receiver) -> None:
    first_body = package_bytes(synthetic_package("1.7.0", "SYNTHETIC-FIRST"))
    second_body = package_bytes(synthetic_package("1.7.0", "SYNTHETIC-SECOND"))
    first_status, _, first_response = receiver.upload(
        first_body, filename="synthetic-duplicate.json"
    )
    second_status, _, second_response = receiver.upload(
        second_body, filename="synthetic-duplicate.json"
    )
    assert first_status == second_status == 200
    first_path = assert_stored(receiver, first_response, first_body)
    second_path = assert_stored(receiver, second_response, second_body)
    assert first_path != second_path


def test_explicit_wrong_token_is_rejected(receiver: Receiver) -> None:
    status, _, response = receiver.upload(
        package_bytes(synthetic_package("1.7.0")), token="wrong-synthetic-token"
    )
    assert status == 401, response
    assert json.loads(response)["ok"] is False


def test_required_token_mode_rejects_missing_header(required_receiver: Receiver) -> None:
    status, _, response = required_receiver.upload(package_bytes(synthetic_package("1.7.0")))
    assert status == 401, response
    assert json.loads(response)["ok"] is False


def test_required_token_mode_accepts_matching_header(required_receiver: Receiver) -> None:
    body = package_bytes(synthetic_package("1.7.0"))
    status, _, response = required_receiver.upload(body, token=TEST_TOKEN)
    assert status == 200, response
    assert_stored(required_receiver, response, body)


@pytest.mark.parametrize(
    ("body", "expected_status", "expected_error"),
    [
        (b'{"schemaVersion":', 400, "invalid_json"),
        (b'{"schemaVersion":"1.7.0"}', 422, "missing_schema_version_or_session_id"),
    ],
)
def test_invalid_payloads_return_contract_errors(
    receiver: Receiver,
    body: bytes,
    expected_status: int,
    expected_error: str,
) -> None:
    status, _, response = receiver.upload(body)
    assert status == expected_status, response
    assert json.loads(response) == {"ok": False, "error": expected_error}


def test_browser_preflight_allows_upload_headers(required_receiver: Receiver) -> None:
    status, headers, body = required_receiver.request(
        "OPTIONS",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-filename,x-upload-token",
        },
    )
    normalized_headers = {name.lower(): value for name, value in headers.items()}
    assert status == 204
    assert body == b""
    assert normalized_headers["access-control-allow-origin"] == "*"
    allowed_headers = {
        entry.strip().lower()
        for entry in normalized_headers["access-control-allow-headers"].split(",")
    }
    assert {"content-type", "x-filename", "x-upload-token"} <= allowed_headers
    assert "POST" in normalized_headers["access-control-allow-methods"]
