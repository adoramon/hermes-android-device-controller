import unittest
from unittest.mock import patch

from hermes_android_controller.ghostmapx import (
    GHOSTMAPX_CONFIRM_TEXT,
    apply_ghostmapx_location,
    geocode_address,
)


class GhostmapxTests(unittest.TestCase):
    def test_amap_geocode_formats_ghostmapx_coordinate_text(self):
        payload = {
            "status": "1",
            "geocodes": [
                {
                    "formatted_address": "北京市朝阳区望京SOHO",
                    "location": "116.470630,40.010027",
                }
            ],
        }

        with patch.dict("os.environ", {"GHOSTMAPX_AMAP_KEY": "test-key"}, clear=False):
            with patch("hermes_android_controller.ghostmapx._http_json", return_value=payload):
                result = geocode_address("望京SOHO", provider="amap", random_radius_meters=0)

        self.assertTrue(result["ok"])
        self.assertEqual(result["coordinates"]["longitude"], 116.47063)
        self.assertEqual(result["coordinates"]["latitude"], 40.010027)
        self.assertEqual(result["coordinates"]["ghostmapx_text"], "116.470630,40.010027")
        self.assertEqual(result["coordinates"]["random_radius_meters"], 0.0)

    def test_nominatim_geocode_formats_ghostmapx_coordinate_text(self):
        payload = [{"display_name": "Shanghai", "lon": "121.473701", "lat": "31.230416"}]

        with patch("hermes_android_controller.ghostmapx._http_json", return_value=payload):
            result = geocode_address("上海人民广场", provider="nominatim", random_radius_meters=0)

        self.assertTrue(result["ok"])
        self.assertEqual(result["coordinates"]["ghostmapx_text"], "121.473701,31.230416")

    def test_geocode_randomizes_within_default_50_meter_radius(self):
        payload = [{"display_name": "Shanghai", "lon": "121.473701", "lat": "31.230416"}]

        with patch("hermes_android_controller.ghostmapx._http_json", return_value=payload):
            result = geocode_address("上海人民广场", provider="nominatim")

        self.assertTrue(result["ok"])
        coordinates = result["coordinates"]
        self.assertEqual(coordinates["center_longitude"], 121.473701)
        self.assertEqual(coordinates["center_latitude"], 31.230416)
        self.assertEqual(coordinates["random_radius_meters"], 50.0)
        self.assertGreaterEqual(coordinates["random_offset_meters"], 0)
        self.assertLessEqual(coordinates["random_offset_meters"], 50.0)

    def test_apply_requires_explicit_confirmation(self):
        result = apply_ghostmapx_location("上海人民广场", confirm_text="")

        self.assertFalse(result["ok"])
        self.assertEqual(result["required_confirm_text"], GHOSTMAPX_CONFIRM_TEXT)


if __name__ == "__main__":
    unittest.main()
