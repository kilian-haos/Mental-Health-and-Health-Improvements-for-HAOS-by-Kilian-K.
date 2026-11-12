"""Translations: en/de have the same keys, every entity/service/issue is translated, frontend texts complete."""
import json
import re
import sys
import unittest
from pathlib import Path

import _path

ROOT0 = _path.INT
HUB_DEFS = _path._load("mh_entity_defs", ROOT0 / "entity_defs.py").HUB_DEFS
PERSON_DEFS = sys.modules["mh_entity_defs"].PERSON_DEFS
STRINGS = _path._load("mh_i18n", ROOT0 / "i18n.py").STRINGS

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "custom_components" / "mental_health"


def keys(d, prefix=""):
    out = set()
    for k, v in d.items():
        p = f"{prefix}.{k}" if prefix else k
        out |= keys(v, p) if isinstance(v, dict) else {p}
    return out


class Translations(unittest.TestCase):
    def setUp(self):
        self.en = json.loads((INT / "translations" / "en.json").read_text(encoding="utf-8"))
        self.de = json.loads((INT / "translations" / "de.json").read_text(encoding="utf-8"))

    def test_same_keys(self):
        self.assertEqual(keys(self.en), keys(self.de))

    def test_entities_translated(self):
        for d in PERSON_DEFS + HUB_DEFS:
            self.assertIn(d.key, self.en["entity"][d.platform], d.key)
            if d.kind == "enum":
                self.assertEqual(set(self.en["entity"][d.platform][d.key]["state"]), set(d.options))

    def test_services_translated(self):
        import yaml
        services = yaml.safe_load((INT / "services.yaml").read_text(encoding="utf-8"))
        for name, spec in services.items():
            self.assertIn(name, self.en["services"], name)
            for f in ((spec or {}).get("fields") or {}):
                self.assertIn(f, self.en["services"][name]["fields"], f"{name}.{f}")
            for f in ((spec or {}).get("fields") or {}).values():
                tk = ((f.get("selector") or {}).get("select") or {}).get("translation_key")
                if tk:
                    self.assertIn(tk, self.en["selector"])

    def test_registered_services_documented(self):
        import yaml
        services = set(yaml.safe_load((INT / "services.yaml").read_text(encoding="utf-8")))
        code = (INT / "services.py").read_text(encoding="utf-8")
        registered = set(re.findall(r'async_register\(DOMAIN, "([a-z_]+)"', code))
        self.assertEqual(registered, services)

    def test_exceptions_used_are_translated(self):
        used = set()
        for py in INT.rglob("*.py"):
            used |= set(re.findall(r'translation_key="([a-z_]+)"', py.read_text(encoding="utf-8")))
        used |= {f"backup_{c}" for c in ("no_password", "wrong_password", "invalid_file", "not_found", "invalid_name", "password_short")}
        for k in {u for u in used if not u.endswith("_")} - {"missing_target", "missing_entity"}:
            self.assertIn(k, self.en["exceptions"], k)

    def test_own_strings_en_de(self):
        self.assertEqual(set(STRINGS["en"]), set(STRINGS["de"]))

    def test_frontend_i18n_complete(self):
        for name in ("mental-health.js", "mental-health-panel.js"):
            js = (INT / "frontend" / name).read_text(encoding="utf-8")
            if name == "mental-health.js":
                en = js[js.index("  en: {"):js.index("  de: {")]
                de = js[js.index("  de: {"):js.index("const normLang")]
            else:
                en = js[js.index("Object.assign(M.I18N.en, {"):js.index("Object.assign(M.I18N.de, {")]
                de = js[js.index("Object.assign(M.I18N.de, {"):js.index("const PCSS")]
            ke = set(re.findall(r"(?:^|[,{])\s*([a-z][a-z0-9_]*):\s*[\"`]", en, re.M)) - {"en", "de"}
            kd = set(re.findall(r"(?:^|[,{])\s*([a-z][a-z0-9_]*):\s*[\"`]", de, re.M)) - {"en", "de"}
            self.assertEqual(ke - kd, set(), f"{name}: missing in de")
            self.assertEqual(kd - ke, set(), f"{name}: missing in en")

    def test_every_ws_command_accepts_session_fields(self):
        """The card sends session + admin_session with every call – all commands must accept them."""
        code = (INT / "websocket.py").read_text(encoding="utf-8")
        self.assertEqual(code.count("websocket_api.websocket_command("), 1)      # nur in _cmd()
        n_cmds = len(re.findall(r"^@_cmd\(", code, re.M))
        n_funcs = len(re.findall(r"^(?:async )?def ws_", code, re.M))
        self.assertEqual(n_cmds, n_funcs)
        self.assertNotIn("require_admin", code)

    def test_versions_match(self):
        man = json.loads((INT / "manifest.json").read_text(encoding="utf-8"))["version"]
        const = re.search(r'VERSION = "([\d.]+)"', (INT / "const.py").read_text(encoding="utf-8")).group(1)
        js = re.search(r'const VERSION = "([\d.]+)"', (INT / "frontend" / "mental-health.js").read_text(encoding="utf-8")).group(1)
        self.assertEqual({man, const, js}, {man})


if __name__ == "__main__":
    unittest.main()
