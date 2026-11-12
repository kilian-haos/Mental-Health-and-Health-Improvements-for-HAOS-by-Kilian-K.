"""Runtime with the HA stub: persons, check-ins, privacy, PINs, notifications, backup, migration."""
import asyncio
import json
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path

import _path  # noqa: F401
import ha_stub as H

H.install()
ROOT = Path(__file__).resolve().parent.parent
# Paket ohne __init__.py laden (das braucht Frontend/HTTP aus echtem HA)
for name, path in (("custom_components", ROOT / "custom_components"),
                   ("custom_components.mental_health", ROOT / "custom_components" / "mental_health")):
    if name not in sys.modules:
        m = types.ModuleType(name)
        m.__path__ = [str(path)]
        sys.modules[name] = m

from custom_components.mental_health import archive  # noqa: E402
from custom_components.mental_health.logic import permissions as PM  # noqa: E402
from custom_components.mental_health.runtime import MHRuntime  # noqa: E402
from custom_components.mental_health.storage import Locked  # noqa: E402

ADMIN = H.FakeUser("u_admin", True, "Kilian")
ANNA = H.FakeUser("u_anna", False, "Anna")
LENA = H.FakeUser("u_lena", False, "Lena")
NEW = H.FakeUser("u_new", False, "Neu")



class Base(unittest.TestCase):
    def setUp(self):
        H.reset()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.hass = H.FakeHass("de")
        for eid, uid, name in (("person.kilian_k", "u_admin", "Kilian"), ("person.anna_k", "u_anna", "Anna"),
                               ("person.lena_k", "u_lena", "Lena"), ("person.neu_k", "u_new", "Neu"),
                               ("person.gast", None, "Gast")):
            self.hass.states.set(eid, "home", {"user_id": uid, "friendly_name": name})
        self.rt = self.make()
        self.kilian = self.aw(self.rt.async_create_person("person.kilian_k", {
            "sex": "male", "birthdate": "1990-05-17", "height_cm": 182,
            "modules": {"weight": True},
            "targets": [{"kind": "service", "service": "notify.mobile_app_s25"},
                        {"kind": "service", "service": "notify.mobile_app_ipad"}]}))
        self.anna = self.aw(self.rt.async_create_person("person.anna_k", {"sex": "female", "modules": {"cycle": True},
                                                                          "can_edit_own": True}))
        self.lena = self.aw(self.rt.async_create_person("person.lena_k", {"child": True, "birthdate": "2016-03-02",
                                                                          "sex": "female"}))

    def tearDown(self):
        self.loop.close()

    def aw(self, coro):
        return self.loop.run_until_complete(coro)

    def make(self):
        rt = MHRuntime(self.hass, H.FakeEntry())
        self.aw(rt.async_setup())
        return rt

    def evening(self, p, mood=7, journal="Langer Spaziergang im Wald mit Freunden", **extra):
        data = {"mood": mood, "good": ["Spaziergang"], "bad": ["Regen"], "trained": {"done": False},
                "journal": journal, **extra}
        if p.mod("cycle"):
            data.setdefault("period", {"answer": "no"})
        return self.aw(self.rt.async_submit(p, "evening", self.rt.clock().today, data))


class Persons(Base):
    def test_only_persons_with_user(self):
        with self.assertRaises(ValueError):
            self.aw(self.rt.async_create_person("person.gast"))
        with self.assertRaises(ValueError):
            self.aw(self.rt.async_create_person("person.kilian_k"))
        hp = {p["entity_id"]: p for p in self.rt.ha_persons()}
        self.assertFalse(hp["person.gast"]["eligible"])
        self.assertTrue(hp["person.kilian_k"]["taken"])

    def test_child_defaults(self):
        self.assertFalse(self.lena.profile["can_edit_own"])
        self.assertFalse(self.lena.mod("weight"))
        self.assertFalse(self.lena.mod("cycle"))          # nur wenn ein Admin es erlaubt
        self.assertFalse(self.lena.mod("llm"))

    def test_cycle_only_female_other(self):
        self.assertFalse(self.kilian.mod("cycle"))
        self.assertTrue(self.anna.mod("cycle"))

    def test_preview_for_not_set_up(self):
        me = self.rt.me_payload(NEW)
        self.assertFalse(me["setup"])
        self.assertIsNone(me["request"])

    def test_setup_request_cooldown_and_admin_notice(self):
        r1 = self.aw(self.rt.async_request_setup(NEW))
        self.assertTrue(r1["sent"])
        self.assertEqual(len(H.NOTIFICATIONS), 1)            # keine Admin-Ziele -> HA-Mitteilung
        r2 = self.aw(self.rt.async_request_setup(NEW))
        self.assertFalse(r2["sent"])
        self.rt.settings["admin_targets"] = [{"id": "a", "kind": "service", "service": "notify.mobile_app_s25", "name": "x"}]
        H.advance(60 * 25)
        self.aw(self.rt.async_request_setup(NEW))
        self.assertEqual(self.hass.services.calls[-1][1], "mobile_app_s25")
        self.assertIn("Neu", self.hass.services.calls[-1][2]["message"])

    def test_delete_person_removes_stores(self):
        pid = self.anna.pid
        self.aw(self.rt.async_delete_person(pid))
        self.assertNotIn(f"mental_health.person.{pid}", H.STORES)
        self.assertNotIn(pid, self.rt.keyring.persons)


class Checkins(Base):
    def test_evening_required_and_saved(self):
        today = self.rt.clock().today
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        res = self.aw(self.rt.async_submit(self.kilian, "evening", today, {"mood": 7}))
        self.assertFalse(res["ok"])
        self.assertEqual(set(res["errors"]), {"good", "bad", "trained"})
        res = self.evening(self.kilian)
        self.assertTrue(res["ok"], res)
        self.assertEqual(self.rt.values[self.kilian.pid]["mood_evening"], 7)

    def test_evening_not_before_14h(self):
        H.set_now(datetime(2026, 11, 11, 10, 0, tzinfo=H.TZ))
        res = self.evening(self.kilian)
        self.assertEqual(res["errors"], {"_": "not_allowed"})

    def test_contents_encrypted_at_rest(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.kilian, journal="GEHEIMER Satz über Oma")
        self.aw(self.rt.async_save_all())
        dump = json.dumps(H.STORES)
        self.assertNotIn("GEHEIMER", dump)
        self.assertNotIn("Spaziergang", dump)
        # Konfiguration enthält keine Einträge
        self.assertNotIn('"_ts"', json.dumps(H.STORES["mental_health.config"]))
        self.assertNotIn('"mood": 7', json.dumps(H.STORES["mental_health.config"]))

    def test_admin_sees_no_contents(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.anna, journal="Anna privat")
        admin = json.dumps(self.rt.admin_payload())
        self.assertNotIn("Anna privat", admin)
        self.assertNotIn("Spaziergang", admin)
        v = self.rt.viewer(ADMIN)
        self.assertFalse(PM.allowed(v, PM.CONTENT, self.anna.rights))
        # Entitätswerte: keine Texte, keine Zyklus-Details
        vals = json.dumps(self.rt.values[self.anna.pid])
        self.assertNotIn("Anna privat", vals)
        self.assertNotIn("flow", vals)

    def test_manual_entry_closes_window_and_clears_notifications(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.aw(self.rt.open_window(self.kilian.pid, "evening"))
        sent = [c for c in self.hass.services.calls if c[2].get("message") != "clear_notification"]
        self.assertEqual(len(sent), 2)                       # pro Gerät einzeln
        android = next(c for c in sent if c[1] == "mobile_app_s25")[2]["data"]
        self.assertTrue(android["persistent"])
        self.assertEqual(android["tag"], f"mh_{self.kilian.pid}_evening_0")
        self.assertEqual(android["clickAction"], "/mental-health?checkin=evening")
        ios = next(c for c in sent if c[1] == "mobile_app_ipad")[2]["data"]
        self.assertEqual(ios["push"]["interruption-level"], "time-sensitive")
        self.assertNotIn("persistent", ios)
        self.hass.services.calls.clear()
        self.evening(self.kilian)
        self.assertFalse(self.rt.window_open(self.kilian.pid, "evening"))
        clears = [c for c in self.hass.services.calls if c[2].get("message") == "clear_notification"]
        self.assertEqual(len(clears), 2)

    def test_lock_screen_without_sensitive_content(self):
        H.set_now(datetime(2026, 11, 11, 7, 30, tzinfo=H.TZ))
        self.aw(self.rt.open_window(self.kilian.pid, "morning"))
        msg = self.hass.services.calls[0][2]["message"]
        self.assertNotIn("kg", msg)
        self.assertEqual(msg, "Dein Morgen-Check-in ist bereit.")

    def test_window_missed(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.aw(self.rt.open_window(self.kilian.pid, "evening"))
        H.advance(61)
        self.aw(self.rt._tick())
        self.assertFalse(self.rt.window_open(self.kilian.pid, "evening"))
        st = self.kilian.day_numbers(self.rt.clock().today)["status"]["evening"]
        self.assertEqual(st, "missed")

    def test_schedule_fixed_time_opens_window(self):
        H.set_now(datetime(2026, 11, 11, 7, 30, 30, tzinfo=H.TZ))
        self.aw(self.rt._tick())
        self.assertTrue(self.rt.window_open(self.kilian.pid, "morning"))
        self.aw(self.rt._tick())
        self.assertEqual(len([c for c in self.hass.services.calls if c[1] == "mobile_app_s25"]), 1)   # nicht doppelt

    def test_pause_no_checkins(self):
        self.aw(self.rt.async_set_pause(self.kilian.pid, True, None))
        H.set_now(datetime(2026, 11, 11, 7, 31, tzinfo=H.TZ))
        self.aw(self.rt._tick())
        self.assertFalse(self.rt.window_open(self.kilian.pid, "morning"))
        self.assertTrue(self.rt.values[self.kilian.pid]["paused"])


class Android14(Base):
    def setUp(self):
        super().setUp()
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.aw(self.rt.open_window(self.kilian.pid, "evening"))
        self.hass.services.calls.clear()

    def swipe(self, idx=0, slot="evening"):
        self.hass.bus.fire("mobile_app_notification_cleared", {"tag": f"mh_{self.kilian.pid}_{slot}_{idx}"})
        self.aw(self.hass.drain())

    def test_resend_only_to_swiping_device(self):
        self.swipe(0)
        self.assertEqual([c[1] for c in self.hass.services.calls], ["mobile_app_s25"])
        self.assertTrue(self.hass.services.calls[0][2]["data"]["alert_once"])

    def test_no_resend_for_ios(self):
        self.swipe(1)
        self.assertEqual(self.hass.services.calls, [])

    def test_rate_limit(self):
        self.swipe(0)
        self.swipe(0)
        self.assertEqual(len(self.hass.services.calls), 1)

    def test_no_resend_after_window(self):
        self.evening(self.kilian)
        self.hass.services.calls.clear()
        self.swipe(0)
        self.assertEqual(self.hass.services.calls, [])

    def test_foreign_tags_ignored(self):
        self.hass.bus.fire("mobile_app_notification_cleared", {"tag": "fenster_kueche"})
        self.aw(self.hass.drain())
        self.assertEqual(self.hass.services.calls, [])

    def test_broken_target_does_not_block(self):
        self.kilian.profile["targets"].insert(0, {"id": "b", "kind": "service", "service": "notify.mobile_app_broken", "name": "kaputt"})
        self.hass.services.fail.add("notify.mobile_app_broken")
        n = self.aw(self.rt.send_checkin(self.kilian, "evening"))
        self.assertEqual(n, 2)


class Pins(Base):
    def test_person_pin_protects_texts(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.anna, journal="Vor der PIN")
        res = self.aw(self.rt.async_set_pin("u_anna", None, "4711"))
        self.assertTrue(res["ok"])
        tok = res["token"]
        self.assertTrue(self.rt.person_session_ok(self.anna, "u_anna", tok))
        self.assertFalse(self.rt.person_session_ok(self.anna, "u_anna", None))
        self.assertFalse(self.rt.person_session_ok(self.anna, "u_admin", tok))     # Token gehört Anna
        self.rt.lock_person(self.anna.pid)
        with self.assertRaises(Locked):
            self.anna.vault.texts(self.rt.clock().today.isoformat())
        # Zahlen laufen weiter (Sensoren)
        self.rt.recompute(self.anna.pid)
        self.assertEqual(self.rt.values[self.anna.pid]["mood_evening"], 7)
        bad = self.aw(self.rt.async_unlock_person("u_anna", "0000"))
        self.assertFalse(bad["ok"])
        ok = self.aw(self.rt.async_unlock_person("u_anna", "4711"))
        self.assertTrue(ok["ok"])
        self.assertEqual(self.anna.vault.texts(self.rt.clock().today.isoformat())["e"]["journal"], "Vor der PIN")

    def test_pin_lockout(self):
        self.aw(self.rt.async_set_pin("u_anna", None, "4711"))
        self.rt.lock_person(self.anna.pid)
        for _ in range(3):
            self.aw(self.rt.async_unlock_person("u_anna", "1111"))
        r = self.aw(self.rt.async_unlock_person("u_anna", "4711"))
        self.assertFalse(r["ok"])
        self.assertIn("locked_until", r)

    def test_admin_reset_loses_texts_keeps_numbers(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.anna, journal="weg nach Reset")
        self.aw(self.rt.async_set_pin("u_anna", None, "4711"))
        res = self.aw(self.rt.async_reset_pin(self.anna.pid))
        self.assertEqual(res["lost"], 1)
        self.assertIsNone(self.anna.vault.texts(self.rt.clock().today.isoformat()))
        self.assertEqual(self.anna.record(self.rt.clock().today.isoformat())["mood_e"], 7)
        self.assertFalse(self.rt.keyring.has_pin(self.anna.pid))

    def test_admin_pin(self):
        self.assertTrue(self.rt.admin_session_ok("u_admin", None))
        self.aw(self.rt.async_set_admin_pin("2468"))
        self.assertFalse(self.rt.admin_session_ok("u_admin", None))
        r = self.aw(self.rt.async_admin_unlock("u_admin", "2468"))
        self.assertTrue(self.rt.admin_session_ok("u_admin", r["token"]))
        self.assertNotIn("2468", json.dumps(self.rt._config_data()))

    def test_pin_survives_restart(self):
        self.aw(self.rt.async_set_pin("u_anna", None, "4711"))
        self.aw(self.rt.async_save_all())
        rt2 = self.make()
        anna2 = rt2.person_for_user("u_anna")
        self.assertIsNone(anna2.vault.tek)
        self.assertTrue(self.aw(rt2.async_unlock_person("u_anna", "4711"))["ok"])


class UnifiedPin(Base):
    """One PIN field: personal PIN, or the admin PIN instead (admin rights for this session only)."""

    def setUp(self):
        super().setUp()
        self.aw(self.rt.async_set_admin_pin("2468"))
        self.aw(self.rt.async_set_pin("u_admin", None, "1357"))
        self.aw(self.rt.async_set_pin("u_anna", None, "4711"))
        self.rt.lock_user("u_admin")
        self.rt.lock_user("u_anna")

    def test_admin_with_personal_pin_gets_admin_area(self):
        self.assertFalse(self.rt.admin_access(ADMIN, None))
        r = self.aw(self.rt.async_unlock(ADMIN, "1357"))
        self.assertTrue(r["ok"])
        self.assertTrue(r["token"] and r["admin_token"])
        self.assertFalse(r["elevated"])
        self.assertTrue(self.rt.admin_access(ADMIN, r["admin_token"]))
        self.assertTrue(self.rt.person_session_ok(self.kilian, "u_admin", r["token"]))

    def test_non_admin_personal_pin_no_admin(self):
        r = self.aw(self.rt.async_unlock(ANNA, "4711"))
        self.assertTrue(r["ok"])
        self.assertNotIn("admin_token", r)
        self.assertFalse(self.rt.admin_access(ANNA, r.get("admin_token")))
        self.assertFalse(self.rt.viewer(ANNA, None).is_admin)

    def test_admin_pin_instead_elevates_this_session_only(self):
        r = self.aw(self.rt.async_unlock(ANNA, "2468"))
        self.assertTrue(r["ok"])
        self.assertTrue(r["elevated"])
        tok = r["admin_token"]
        self.assertTrue(self.rt.admin_access(ANNA, tok))
        self.assertTrue(self.rt.viewer(ANNA, tok).is_admin)
        me = self.rt.me_payload(ANNA, tok)
        self.assertTrue(me["admin_elevated"] and me["is_admin"] and me["admin_access"])
        self.assertFalse(self.rt.me_payload(ANNA, None)["is_admin"])       # andere Sitzung: nichts
        self.assertFalse(self.rt.admin_access(LENA, tok))                    # Token gehört Anna
        # Admin-PIN entschlüsselt keine Texte
        self.assertIsNone(self.anna.vault.tek)
        self.rt.lock_user("u_anna")
        self.assertFalse(self.rt.admin_access(ANNA, tok))

    def test_wrong_pin_and_lockout(self):
        for _ in range(3):
            self.assertFalse(self.aw(self.rt.async_unlock(ANNA, "0000"))["ok"])
        r = self.aw(self.rt.async_unlock(ANNA, "4711"))
        self.assertFalse(r["ok"])
        self.assertIn("locked_until", r)

    def test_admin_pin_unset_no_elevation(self):
        self.aw(self.rt.async_set_admin_pin(None))
        r = self.aw(self.rt.async_unlock(ANNA, "2468"))
        self.assertFalse(r["ok"])
        self.assertTrue(self.rt.admin_access(ADMIN, None))                 # ohne Admin-PIN: Admins frei
        self.assertFalse(self.rt.admin_access(ANNA, None))


class Profile(Base):
    def test_rights_on_update(self):
        v_lena = self.rt.viewer(LENA)
        refused = self.rt.update_profile(self.lena.pid, {"height_cm": 150, "schedule": {"sleep_gap_min": 30}}, v_lena)
        self.assertEqual(refused, {"height_cm": "child", "schedule": "child"})
        v_anna = self.rt.viewer(ANNA)
        refused = self.rt.update_profile(self.anna.pid, {"height_cm": 170, "child": True}, v_anna)
        self.assertEqual(refused, {"child": "admin_only"})
        self.assertEqual(self.anna.profile["height_cm"], 170)
        refused = self.rt.update_profile(self.anna.pid, {"modules": {"journal": False}}, self.rt.viewer(ADMIN))
        self.assertEqual(refused, {})
        self.assertFalse(self.anna.mod("journal"))

    def test_target_weight_clamped(self):
        self.rt.update_profile(self.kilian.pid, {"target_weight": 50}, self.rt.viewer(ADMIN))
        self.assertGreaterEqual(self.kilian.profile["target_weight"], 61.0)

    def test_module_off_removes_entities(self):
        from custom_components.mental_health.entity_defs import person_entity_keys
        self.assertIn("weight_due", person_entity_keys(self.kilian))
        self.rt.update_profile(self.kilian.pid, {"modules": {"weight": False}}, self.rt.viewer(ADMIN))
        self.assertNotIn("weight_due", person_entity_keys(self.kilian))
        self.assertNotIn("sleeping", person_entity_keys(self.kilian))      # keine Schlafquelle
        self.assertNotIn("cycle_active", person_entity_keys(self.kilian))

    def test_live_weight_hidden_from_admin(self):
        self.rt.update_profile(self.kilian.pid, {"weight_kg": 80, "weight_live": True}, self.rt.viewer(ANNA))
        self.rt.update_profile(self.anna.pid, {"weight_kg": 60, "weight_live": True, "modules": {"weight": True}},
                               self.rt.viewer(ANNA))
        adm = self.rt.admin_payload()
        anna = next(p for p in adm["persons"] if p["profile"]["id"] == self.anna.pid)
        self.assertIsNone(anna["profile"]["weight_kg"])
        from custom_components.mental_health.entity_defs import person_entity_keys
        self.assertNotIn("weight_profile", person_entity_keys(self.anna))

    def test_repairs_for_missing_source(self):
        self.rt.update_profile(self.kilian.pid, {"sleep_sources": [
            {"entity": "sensor.esp_32_01_master_bed_sensor", "kind": "numeric"}]}, self.rt.viewer(ADMIN))
        self.assertTrue(any(k.startswith("missing_") for k in H.ISSUES))
        issue = next(v for k, v in H.ISSUES.items() if k.startswith("missing_"))
        self.rt.fix_issue(issue["data"])
        self.assertEqual(self.kilian.profile["sleep_sources"], [])
        self.assertFalse(any(k.startswith("missing_") for k in H.ISSUES))


class Family(Base):
    def test_k_threshold(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.kilian, 8)
        self.evening(self.anna, 6)
        fam = self.rt.family_payload(self.rt.viewer(ANNA))
        self.assertFalse(fam["enough"])
        self.assertIsNone(fam["mood"])
        self.evening(self.lena, 7)
        fam = self.rt.family_payload(self.rt.viewer(ANNA))
        self.assertTrue(fam["enough"])
        self.assertEqual(fam["mood"], 7.0)
        self.assertNotIn("Anna", json.dumps({k: v for k, v in fam.items() if k != "birthdays"}))
        self.assertEqual(self.rt.hub_values["family_mood"], 7.0)

    def test_birthdays_same_day(self):
        self.rt.update_profile(self.anna.pid, {"birthdate": "--03-02"}, self.rt.viewer(ADMIN))
        H.set_now(datetime(2027, 3, 2, 9, 0, tzinfo=H.TZ))
        self.rt.recompute_all()
        self.assertEqual(self.rt.hub_values["birthdays_today"], 2)
        self.assertEqual(sorted(self.rt.hub_values["birthdays_today_names"]), ["Anna", "Lena"])


class Dashboard(Base):
    def test_dashboard_and_search(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.kilian, 8, journal="Spaziergang am See")
        d = self.rt.dashboard_payload(self.kilian)
        self.assertEqual(d["values"]["mood_today"], 8.0)
        self.assertTrue(d["evening_manual"])
        self.assertEqual(d["days"][0]["mood"], 8.0)
        from custom_components.mental_health.person import search_records
        res, chips = search_records(self.kilian, "See", None, self.rt.clock().today)
        self.assertEqual(len(res), 1)

    def test_low_mood_protect_only_own(self):
        for i in range(3):
            H.set_now(datetime(2026, 11, 9 + i, 21, 0, tzinfo=H.TZ))
            self.evening(self.anna, 2)
        d = self.rt.dashboard_payload(self.anna)
        self.assertTrue(d["protect"])
        # kein Sensor, keine Benachrichtigung an andere
        self.assertNotIn("protect", json.dumps(self.rt.values[self.anna.pid]))

    def test_morning_form_and_training_flow(self):
        H.set_now(datetime(2026, 11, 9, 21, 0, tzinfo=H.TZ))
        self.evening(self.kilian, trained={"done": True, "type": "strength", "minutes": 45})
        H.set_now(datetime(2026, 11, 10, 7, 40, tzinfo=H.TZ))
        form = self.rt.checkin_form(self.kilian, "morning")
        self.assertIn("soreness", [f["key"] for f in form["fields"]])
        H.set_now(datetime(2026, 11, 12, 7, 40, tzinfo=H.TZ))
        self.aw(self.rt.async_submit(self.kilian, "morning", self.rt.clock().today, {"mood": 6, "soreness": 1}))
        self.rt.recompute(self.kilian.pid)
        self.assertEqual(self.rt.values[self.kilian.pid]["training_status"], "recommended")

    def test_export_contains_only_own(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.kilian, journal="Kilian Text")
        self.evening(self.anna, journal="Anna Text")
        recs = json.dumps(self.kilian.records(with_texts=True))
        self.assertIn("Kilian Text", recs)
        self.assertNotIn("Anna Text", recs)


class BackupMigration(Base):
    def test_backup_roundtrip_and_restore(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.kilian, journal="im Backup")
        with self.assertRaises(archive.BackupError):
            self.aw(archive.async_create(self.rt))
        archive.set_password(self.rt, "sehr-geheim")
        res = self.aw(archive.async_create(self.rt))
        blob = archive.read_file(self.rt, res["name"])
        self.assertNotIn(b"im Backup", blob)
        pre = archive.preview(blob, "sehr-geheim")
        self.assertEqual(len(pre["persons"]), 3)
        with self.assertRaises(archive.BackupError):
            archive.preview(blob, "falsch")
        # Daten ändern, dann wiederherstellen
        self.aw(self.rt.async_delete_person(self.anna.pid))
        out = self.aw(archive.async_restore(self.rt, blob, "sehr-geheim"))
        self.assertTrue(out["ok"])
        self.assertIsNotNone(out["safety"])                  # Sicherungspunkt vorher
        rt2 = self.make()
        self.assertEqual(len(rt2.persons), 3)
        k2 = rt2.person_for_user("u_admin")
        self.assertEqual(k2.vault.texts(rt2.clock().today.isoformat())["e"]["journal"], "im Backup")

    def test_delete_backup(self):
        archive.set_password(self.rt, "sehr-geheim")
        res = self.aw(archive.async_create(self.rt))
        names = [b["name"] for b in archive.list_backups(self.rt)]
        self.assertIn(res["name"], names)
        for bad in ("../mental_health.keys", "/etc/passwd", ".x.mhbackup", "x.txt", ""):
            with self.assertRaises(archive.BackupError):
                archive.delete_file(self.rt, bad)
        with self.assertRaises(archive.BackupError):
            archive.delete_file(self.rt, "gibt_es_nicht.mhbackup")
        archive.delete_file(self.rt, res["name"])
        self.assertNotIn(res["name"], [b["name"] for b in archive.list_backups(self.rt)])

    def test_store_migration_hook(self):
        from custom_components.mental_health.storage import migrate_config
        old = {"persons": {}}
        self.assertEqual(set(migrate_config(0, old)), {"persons", "settings", "requests"})
        H.STORES["mental_health.config"]["version"] = 0
        rt2 = self.make()
        self.assertEqual(len(rt2.persons), 3)

    def test_restart_keeps_everything(self):
        H.set_now(datetime(2026, 11, 11, 21, 0, tzinfo=H.TZ))
        self.evening(self.kilian, 9)
        self.aw(self.rt.async_save_all())
        rt2 = self.make()
        k2 = rt2.person_for_user("u_admin")
        self.assertEqual(k2.record(rt2.clock().today.isoformat())["mood_e"], 9)


if __name__ == "__main__":
    unittest.main()
