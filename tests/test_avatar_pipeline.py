import unittest

from src.avatar_pipeline import AvatarRequest, InfraiClient, process_avatar


class FakeClient:
    def upload(self, image, filename):
        return {"ok": True, "data": {"id": "uploaded-1"}}

    def smart_crop(self, image, aspect):
        assert image == "uploaded-1"
        assert aspect == "1:1"
        return {"ok": True, "data": {"id": "avatar-1"}}


class AvatarDecisionTest(unittest.TestCase):
    def test_upload_base64_encodes_binary_image(self):
        client = InfraiClient(api_key="test-key")
        def capture(path, payload):
            self.assertEqual(path, "/v1/image/upload")
            self.assertEqual(payload, {"file": "/wCA", "filename": "face.jpg"})
            return {"ok": True}
        client._post = capture
        self.assertEqual(client.upload(b"\xff\x00\x80", "face.jpg"), {"ok": True})

    def test_ready_avatar_emits_patient_safe_notification(self):
        result = process_avatar(AvatarRequest("p-7", "face.jpg", b"bytes"), FakeClient())
        self.assertEqual(result.image_id, "avatar-1")
        self.assertEqual(result.notification, "appointment-avatar-ready")


if __name__ == "__main__":
    unittest.main()
