import unittest
from io import BytesIO

from fastapi import HTTPException, UploadFile

from app.schemas.vehicle_schema import VehicleResponse


class VehicleImageSchemaTests(unittest.TestCase):
    def test_existing_vehicle_response_accepts_missing_image_url(self):
        vehicle = VehicleResponse.model_validate(
            {
                "id": "507f1f77bcf86cd799439011",
                "vehicle_code": "EV-001",
                "registration_number": "WP CAA-1201",
                "vehicle_type": "electric_van",
                "brand": "BYD",
                "model": "T3",
                "year": 2026,
                "fuel_type": "electric",
                "current_mileage": 1200,
                "status": "active",
                "health_status": "healthy",
                "created_at": "2026-08-16T00:00:00Z",
                "updated_at": "2026-08-16T00:00:00Z",
            }
        )

        self.assertIsNone(vehicle.image_url)


class VehicleImageValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_unsupported_vehicle_image(self):
        from app.services.vehicle_media_service import validate_vehicle_image

        upload = UploadFile(filename="vehicle.svg", file=BytesIO(b"<svg/>"))
        upload.headers = {"content-type": "image/svg+xml"}

        with self.assertRaises(HTTPException) as context:
            await validate_vehicle_image(upload)

        self.assertEqual(context.exception.status_code, 415)

    async def test_rejects_oversized_vehicle_image(self):
        from app.services.vehicle_media_service import MAX_IMAGE_BYTES, validate_vehicle_image

        upload = UploadFile(filename="vehicle.png", file=BytesIO(b"x" * (MAX_IMAGE_BYTES + 1)))
        upload.headers = {"content-type": "image/png"}

        with self.assertRaises(HTTPException) as context:
            await validate_vehicle_image(upload)

        self.assertEqual(context.exception.status_code, 413)

    async def test_accepts_supported_vehicle_image(self):
        from app.services.vehicle_media_service import validate_vehicle_image

        upload = UploadFile(filename="vehicle.webp", file=BytesIO(b"valid-webp-content"))
        upload.headers = {"content-type": "image/webp"}

        content, suffix = await validate_vehicle_image(upload)

        self.assertEqual(content, b"valid-webp-content")
        self.assertEqual(suffix, ".webp")


if __name__ == "__main__":
    unittest.main()
