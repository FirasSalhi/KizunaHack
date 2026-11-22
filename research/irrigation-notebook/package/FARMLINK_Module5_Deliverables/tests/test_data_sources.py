"""Download clients tested against a LOCAL mock HTTP server (the real services were unreachable from the build sandbox)."""
import json, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import numpy as np
import _path  # noqa
from engine import data_sources as D

STATE = {"fails": 0, "hits": 0}
CSV = "Date,Humidite\n2026-05-01 00:00:00,21.5\n2026-05-01 01:00:00,21.4\n2026-05-01 02:00:00,bad\n"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode(); self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        STATE["hits"] += 1; p = self.path
        if p.startswith("/flaky"):
            if STATE["fails"] > 0: STATE["fails"] -= 1; return self._send(503, "busy")
            return self._send(200, json.dumps({"ok": 1}))
        if p.startswith("/redirect"): self.send_response(302); self.send_header("Location", "/ckan?id=x"); self.end_headers(); return
        if p.startswith("/ckan"):
            res = [{"id": "r1", "name": "Humidité du sol 30 cm", "format": "CSV", "url": f"http://127.0.0.1:{self.server.server_port}/data.csv"},
                   {"id": "r2", "name": "Tension capteur 10cm mV", "format": "CSV", "url": f"http://127.0.0.1:{self.server.server_port}/html"},
                   {"id": "r3", "name": "Humidité du sol", "format": "CSV", "url": ""}]
            return self._send(200, json.dumps({"success": True, "result": {"resources": res}}))
        if p.startswith("/badckan"): return self._send(200, json.dumps({"success": False}))
        if p.startswith("/data.csv"): return self._send(200, CSV, "text/csv")
        if p.startswith("/html"): return self._send(200, "<!DOCTYPE html><html>login</html>", "text/html")
        if p.startswith("/om"):
            n = 3; d = {"time": ["2026-05-01", "2026-05-02", "2026-05-03"], "temperature_2m_max": [25, 26, 27], "temperature_2m_min": [12, 13, 14], "temperature_2m_mean": [18, 19, 20],
                        "relative_humidity_2m_mean": [60, 61, 62], "wind_speed_10m_mean": [3.0, 3.0, 3.0], "shortwave_radiation_sum": [20, 21, 22], "precipitation_sum": [0, 1.2, 0], "et0_fao_evapotranspiration": [4, 4.1, 4.2]}
            return self._send(200, json.dumps({"daily": d, "daily_units": {"shortwave_radiation_sum": "MJ/m²"}, "elevation": 12.0}))
        if p.startswith("/power"):
            par = {k: {"20260501": v, "20260502": v, "20260503": -999.0} for k, v in {"T2M": 18.0, "T2M_MAX": 25.0, "T2M_MIN": 12.0, "RH2M": 60.0, "WS2M": 2.0, "ALLSKY_SFC_SW_DWN": 5.5, "PRECTOTCORR": 0.0}.items()}
            return self._send(200, json.dumps({"properties": {"parameter": par}, "parameters": {"ALLSKY_SFC_SW_DWN": {"units": "kW-hr/m^2/day"}}}))
        if p.startswith("/down"): return self._send(500, "boom")
        self._send(404, "nf")


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H); cls.port = cls.srv.server_port; threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.port}"; cls.s = D.make_session(retries=3, backoff=0.01); cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()

    def test_retries_on_503_then_succeeds(self):
        STATE["fails"] = 2; c, prov = D._get(self.base + "/flaky", self.s); self.assertEqual(json.loads(c)["ok"], 1); self.assertEqual(prov["status"], 200)

    def test_follows_redirect(self):
        c, prov = D._get(self.base + "/redirect", self.s); self.assertGreaterEqual(prov["redirects"], 1)

    def test_persistent_failure_raises_not_fabricates(self):
        with self.assertRaises(D.DownloadError) as e: D._get(self.base + "/down", D.make_session(retries=1, backoff=0.01))
        self.assertIn("failed", str(e.exception))

    def test_cache_only_when_allowed_and_flagged(self):
        cp = self.tmp / "c.json"; D._get(self.base + "/flaky", self.s, cache_path=cp)
        dead = D.make_session(retries=0, backoff=0)
        with self.assertRaises(D.DownloadError): D._get("http://127.0.0.1:9/x", dead, cache_path=cp, allow_cache=False, timeout=(1, 1))
        c, prov = D._get("http://127.0.0.1:9/x", dead, cache_path=cp, allow_cache=True, timeout=(1, 1)); self.assertTrue(prov["from_cache"]); self.assertIn("error", prov)

    def test_ckan_validation(self):
        r = D.fetch_station_package("bargou", self.s, self.tmp, base=self.base + "/ckan"); self.assertEqual(len(r["package"]["resources"]), 3)
        with self.assertRaises(D.DownloadError): D.fetch_station_package("bargou", self.s, self.tmp, allow_cache=False, base=self.base + "/badckan")

    def test_resource_discovery_depth_and_channel_from_metadata(self):
        t = D.discover_resources({"resources": D.fetch_station_package("bargou", self.s, self.tmp, base=self.base + "/ckan")["package"]["resources"]}).set_index("resource_id")
        self.assertEqual(t.loc["r1", "depth_cm"], 30); self.assertEqual(t.loc["r1", "channel"], "soil_vwc_percent")
        self.assertEqual(t.loc["r2", "channel"], "voltage_mv"); self.assertEqual(t.loc["r2", "depth_cm"], 10)
        self.assertTrue(np.isnan(t.loc["r3", "depth_cm"]))       # depth never defaulted

    def test_download_rejects_html_and_empty_url(self):
        with self.assertRaises(D.DownloadError): D.download_resource({"resource_id": "r2", "url": self.base + "/html"}, self.s, self.tmp)
        with self.assertRaises(D.DownloadError): D.download_resource({"resource_id": "r3", "url": ""}, self.s, self.tmp)

    def test_parse_keeps_units_and_flags(self):
        p, _ = D.download_resource({"resource_id": "r1", "url": self.base + "/data.csv"}, self.s, self.tmp)
        out = D.parse_sensor_csv(p, {"resource_id": "r1", "channel": "voltage_mv", "depth_cm": None})
        self.assertEqual(out["channel"], "voltage_mv"); self.assertEqual(out["calibration_status"], "uncalibrated_millivolts")
        self.assertTrue(any("millivolts" in n for n in out["notes"])); self.assertTrue(any("depth not stated" in n for n in out["notes"]))
        self.assertEqual(out["rows"], 3); self.assertTrue(np.isnan(out["data"]["value"].iloc[2]))      # 'bad' -> NaN, not silently dropped to 0

    def test_open_meteo_parse_units_and_wind_conversion(self):
        df, prov = D.open_meteo_daily(36.8, 10.1, "2026-05-01", "2026-05-03", self.s, url=self.base + "/om")
        self.assertAlmostEqual(df["u2"].iloc[0], 3.0 * 4.87 / np.log(67.8 * 10 - 5.42), places=6); self.assertEqual(prov["contract_verified_live"], False)
        self.assertEqual(df["weather_source"].iloc[0], "open_meteo_archive")

    def test_nasa_fill_values_and_radiation_units(self):
        df, _ = D.nasa_power_daily(36.8, 10.1, "2026-05-01", "2026-05-03", self.s, url=self.base + "/power")
        self.assertTrue(np.isnan(df["tmean"].iloc[2])); self.assertAlmostEqual(df["rs"].iloc[0], 5.5 * 3.6)

    def test_fallback_is_explicit_and_can_be_disabled(self):
        urls = {"open_meteo": self.base + "/down", "nasa_power": self.base + "/power"}
        fast = D.make_session(retries=0, backoff=0)
        df, prov = D.fetch_weather(36.8, 10.1, "2026-05-01", "2026-05-03", fast, urls=urls)
        self.assertEqual((prov["source_used"], prov["fallback_used"]), ("nasa_power", True)); self.assertFalse(prov["attempts"][0]["ok"]); self.assertEqual(df["weather_source"].iloc[0], "nasa_power")
        with self.assertRaises(D.DownloadError): D.fetch_weather(36.8, 10.1, "2026-05-01", "2026-05-03", fast, allow_fallback=False, urls=urls)
        df2, p2 = D.fetch_weather(36.8, 10.1, "2026-05-01", "2026-05-03", fast, urls={"open_meteo": self.base + "/om"}); self.assertFalse(p2["fallback_used"])

    def test_all_sources_fail_raises_with_kaggle_hint(self):
        with self.assertRaises(D.DownloadError) as e:
            D.fetch_weather(36.8, 10.1, "2026-05-01", "2026-05-03", D.make_session(retries=0, backoff=0), urls={"open_meteo": "http://127.0.0.1:9/a", "nasa_power": "http://127.0.0.1:9/b"})
        self.assertIn("All weather sources failed", str(e.exception))
        self.assertIn("Internet", D.KAGGLE_INTERNET_HELP)

    def test_station_registry_has_five_ids(self):
        self.assertEqual(len(D.STATIONS), 5); self.assertEqual(D.STATIONS["bargou"]["package_id"], "4d6a078a-c041-479a-845b-5a682ad12dd3")


if __name__ == "__main__":
    unittest.main()
