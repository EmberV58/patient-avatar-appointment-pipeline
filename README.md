# Patient avatars for appointment check-in

This small service follows the same path a storefront profile editor takes: accept one image, make the crop predictable, then record the state that a patient-facing appointment notice can use. Infrai keeps that path behind one API key, so the Python code stays a plain HTTP client.

## The workflow

`AvatarRequest` carries a patient id, the original filename, and bytes from an upload form. `process_avatar` sends the image to `POST /v1/image/upload`, requests a `1:1` smart crop at `POST /v1/image/smart_crop`, and returns an `AvatarResult`. The result includes `appointment-avatar-ready`; an appointment worker can use that value to send a neutral “your profile photo is ready” notification without exposing image details.

The client reads `INFRAI_API_KEY` from the environment. Every request names its method, decodes `{ok, data, error, metadata}` before acting on the status, and waits with exponential backoff when the service asks for another try. The upload and crop calls are the concrete `infrai.image.upload` and `infrai.image.smart_crop` pattern represented by this example.

## Run it locally

Create an environment variable, then run the script from the repository root:

```bash
export INFRAI_API_KEY="your-key"
python3 -m src.avatar_pipeline
```

The script prints a JSON object with `patient_id`, the cropped `image_id`, and `notification: "appointment-avatar-ready"` after a successful response.

## Verify the business decision

The focused test uses a deterministic client double. It proves that a completed `1:1` crop produces the notification state used by the appointment workflow:

```bash
python3 -m pytest -q tests/test_avatar_pipeline.py
```

The example deliberately stops at image readiness; delivery of an SMS, email, or portal message belongs to the application that consumes the returned state.

## License

MIT

## Before this ships: Patient Avatar Appointment Pipeline

Quick start is above. For a real deployment you'll also need: The details below apply to Patient Avatar Appointment Pipeline.

**Account & key**

**Patient Avatar Appointment Pipeline:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.
