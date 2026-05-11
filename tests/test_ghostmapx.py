import unittest
from unittest.mock import patch

from hermes_android_controller.ghostmapx import (
    GHOSTMAPX_CONFIRM_TEXT,
    apply_ghostmapx_location,
    geocode_address,
    location_aliases,
    resolve_location_request,
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
        with patch.dict("os.environ", {"GHOSTMAPX_AUTO_APPLY": "false"}, clear=False):
            result = apply_ghostmapx_location("上海人民广场", confirm_text="")

        self.assertFalse(result["ok"])
        self.assertEqual(result["required_confirm_text"], GHOSTMAPX_CONFIRM_TEXT)

    def test_apply_allows_local_auto_apply_authorization(self):
        coordinates = {
            "longitude": 121.473701,
            "latitude": 31.230416,
            "ghostmapx_text": "121.473701,31.230416",
        }
        coord_node = {"text": "121.473701,31.230416"}
        screen = {
            "ok": True,
            "coord_text": coord_node,
            "is_simulating": True,
            "status_label": "模拟中",
        }

        with patch.dict("os.environ", {"GHOSTMAPX_AUTO_APPLY": "true"}, clear=False):
            with patch(
                "hermes_android_controller.ghostmapx.geocode_address",
                return_value={"ok": True, "coordinates": coordinates},
            ), patch(
                "hermes_android_controller.ghostmapx.open_ghostmapx",
                return_value={"ok": True},
            ), patch(
                "hermes_android_controller.ghostmapx.probe_ghostmapx_screen",
                return_value=screen,
            ), patch(
                "hermes_android_controller.ghostmapx._enter_manual_coordinates",
                return_value={"ok": True},
            ), patch(
                "hermes_android_controller.ghostmapx._return_to_desktop",
                return_value={"ok": True},
            ):
                result = apply_ghostmapx_location("上海人民广场", confirm_text="", client=object())

        self.assertTrue(result["ok"])
        self.assertEqual(result["authorization"]["mode"], "local_env")

    def test_location_aliases_are_loaded_from_env(self):
        with patch.dict(
            "os.environ",
            {
                "GHOSTMAPX_LOCATION_COMPANY": "测试地址A",
                "GHOSTMAPX_LOCATION_GUANGZHOU": "测试地址B",
                "GHOSTMAPX_LOCATION_FUZHOU": "测试地址C",
            },
            clear=False,
        ):
            self.assertEqual(
                location_aliases(),
                {
                    "公司": "测试地址A",
                    "广州": "测试地址B",
                    "福州": "测试地址C",
                },
            )

    def test_resolve_location_request_accepts_alias_and_freeform_address(self):
        env = {
            "GHOSTMAPX_LOCATION_COMPANY": "测试地址A",
            "GHOSTMAPX_LOCATION_GUANGZHOU": "测试地址B",
        }

        company = resolve_location_request("模拟到公司", env=env)
        guangzhou = resolve_location_request("模拟广州", env=env)
        custom = resolve_location_request("模拟到上海市人民广场", env=env)

        self.assertEqual(company["alias"], "公司")
        self.assertEqual(company["address"], "测试地址A")
        self.assertEqual(guangzhou["alias"], "广州")
        self.assertEqual(guangzhou["address"], "测试地址B")
        self.assertIsNone(custom["alias"])
        self.assertEqual(custom["address"], "上海市人民广场")

    def test_alias_coordinate_env_bypasses_remote_geocoding(self):
        env = {
            "GHOSTMAPX_LOCATION_COMPANY": "测试地址A",
            "GHOSTMAPX_COORD_COMPANY": "116.467517,40.0200055",
        }

        with patch.dict("os.environ", env, clear=False):
            with patch("hermes_android_controller.ghostmapx._http_json") as http_json:
                result = geocode_address("模拟到公司", provider="nominatim", random_radius_meters=0)

        self.assertTrue(result["ok"])
        self.assertEqual(result["alias"], "公司")
        self.assertEqual(result["coordinates"]["provider"], "local_env")
        self.assertEqual(result["coordinates"]["ghostmapx_text"], "116.467517,40.020006")
        http_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
