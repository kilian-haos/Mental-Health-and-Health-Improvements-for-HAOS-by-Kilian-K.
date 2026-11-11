"""Permission matrix (complete) and encryption / PIN key wrapping."""
import unittest

import _path  # noqa: F401
from logic import crypto as K
from logic import permissions as P

ADMIN = P.Viewer("admin", True)
ADULT = P.Viewer("adult", False)
OTHER = P.Viewer("other", False)
CHILD = P.Viewer("child", False)

ADULT_EDIT = P.PersonRights("adult", can_edit_own=True)
ADULT_RO = P.PersonRights("adult", can_edit_own=False)
KID = P.PersonRights("child", child=True, can_edit_own=True)   # Kinder: Recht wirkt nicht
ADMIN_SELF = P.PersonRights("admin")


class Matrix(unittest.TestCase):
    def ok(self, v, a, p=None):
        return P.allowed(v, a, p)

    def test_admin_only_actions(self):
        for a in (P.MANAGE_PERSONS, P.ADMIN_AREA, P.BACKUP, P.RESET_PIN):
            self.assertTrue(self.ok(ADMIN, a))
            self.assertFalse(self.ok(ADULT, a))
            self.assertEqual(P.check(ADULT, a)[1], P.R_ADMIN_ONLY)

    def test_content_never_for_admin_of_others(self):
        for p in (ADULT_EDIT, ADULT_RO, KID):
            self.assertFalse(self.ok(ADMIN, P.CONTENT, p))
            self.assertEqual(P.check(ADMIN, P.CONTENT, p)[1], P.R_OWN_ONLY)
            self.assertFalse(self.ok(ADMIN, P.CHECKIN, p))
            self.assertFalse(self.ok(OTHER, P.CONTENT, p))
        self.assertTrue(self.ok(ADMIN, P.CONTENT, ADMIN_SELF))
        self.assertTrue(self.ok(ADULT, P.CONTENT, ADULT_RO))
        self.assertTrue(self.ok(CHILD, P.CONTENT, KID))

    def test_profile(self):
        self.assertTrue(self.ok(ADMIN, P.PROFILE_EDIT, ADULT_RO))
        self.assertTrue(self.ok(ADULT, P.PROFILE_EDIT, ADULT_EDIT))
        self.assertFalse(self.ok(ADULT, P.PROFILE_EDIT, ADULT_RO))
        self.assertEqual(P.check(ADULT, P.PROFILE_EDIT, ADULT_RO)[1], P.R_ADMIN_MANAGED)
        self.assertFalse(self.ok(CHILD, P.PROFILE_EDIT, KID))
        self.assertEqual(P.check(CHILD, P.PROFILE_EDIT, KID)[1], P.R_CHILD)
        for v, p in ((ADULT, ADULT_RO), (CHILD, KID), (ADMIN, KID)):
            self.assertTrue(self.ok(v, P.PROFILE_VIEW, p))
        self.assertFalse(self.ok(OTHER, P.PROFILE_VIEW, ADULT_RO))

    def test_modules(self):
        self.assertTrue(self.ok(ADMIN, P.MODULES_EDIT, KID))
        self.assertTrue(self.ok(ADULT, P.MODULES_EDIT, ADULT_EDIT))
        self.assertFalse(self.ok(ADULT, P.MODULES_EDIT, ADULT_RO))
        self.assertFalse(self.ok(CHILD, P.MODULES_EDIT, KID))

    def test_weight(self):
        live = P.PersonRights("adult", can_edit_own=False, weight_live=True)
        self.assertTrue(self.ok(ADMIN, P.WEIGHT_VIEW, ADULT_RO))
        self.assertTrue(self.ok(ADMIN, P.WEIGHT_EDIT, ADULT_RO))
        self.assertFalse(self.ok(ADMIN, P.WEIGHT_VIEW, live))
        self.assertEqual(P.check(ADMIN, P.WEIGHT_VIEW, live)[1], P.R_LIVE_WEIGHT)
        self.assertFalse(self.ok(ADMIN, P.WEIGHT_EDIT, live))
        self.assertTrue(self.ok(ADULT, P.WEIGHT_VIEW, live))
        self.assertTrue(self.ok(ADULT, P.WEIGHT_EDIT, ADULT_EDIT))
        self.assertFalse(self.ok(ADULT, P.WEIGHT_EDIT, ADULT_RO))
        self.assertTrue(self.ok(CHILD, P.WEIGHT_VIEW, KID))
        self.assertFalse(self.ok(CHILD, P.WEIGHT_EDIT, KID))
        self.assertFalse(self.ok(OTHER, P.WEIGHT_VIEW, ADULT_RO))

    def test_schedule_and_pause(self):
        for a in (P.SCHEDULE_EDIT, P.PAUSE):
            self.assertTrue(self.ok(ADMIN, a, KID))
            self.assertTrue(self.ok(ADULT, a, ADULT_RO))
            self.assertTrue(self.ok(ADULT, a, ADULT_EDIT))
            self.assertFalse(self.ok(CHILD, a, KID))
            self.assertFalse(self.ok(OTHER, a, ADULT_RO))

    def test_own_pin(self):
        for v, p in ((ADULT, ADULT_RO), (ADULT, ADULT_EDIT), (CHILD, KID)):
            self.assertTrue(self.ok(v, P.OWN_PIN, p))
        self.assertFalse(self.ok(ADMIN, P.OWN_PIN, ADULT_RO))

    def test_llm_consent(self):
        self.assertTrue(self.ok(ADULT, P.LLM_CONSENT, ADULT_RO))
        self.assertFalse(self.ok(CHILD, P.LLM_CONSENT, KID))
        self.assertTrue(self.ok(CHILD, P.LLM_CONSENT, P.PersonRights("child", child=True, llm_child_allowed=True)))
        self.assertFalse(self.ok(ADMIN, P.LLM_CONSENT, ADULT_RO))

    def test_no_person(self):
        self.assertFalse(self.ok(ADULT, P.CONTENT, None))

    def test_rights_map_complete(self):
        m = P.rights_map(ADULT, ADULT_RO)
        self.assertEqual(set(m), set(P.ALL_ACTIONS))
        self.assertFalse(m[P.PROFILE_EDIT]["ok"])
        self.assertEqual(m[P.PROFILE_EDIT]["why"], P.R_ADMIN_MANAGED)

    def test_user_without_id_never_self(self):
        self.assertFalse(self.ok(P.Viewer(None, False), P.CONTENT, P.PersonRights(None)))


class Crypto(unittest.TestCase):
    def test_roundtrip_json(self):
        k = K.new_key()
        tok = K.encrypt_json(k, {"journal": "Heute war schön ✓"})
        self.assertNotIn("schön", tok)
        self.assertEqual(K.decrypt_json(k, tok), {"journal": "Heute war schön ✓"})
        with self.assertRaises(K.CryptoError):
            K.decrypt_json(K.new_key(), tok)

    def test_keyring_and_pin(self):
        ring = K.Keyring()
        ring.ensure_person("p1")
        dek = ring.dek("p1")
        tek = ring.tek_without_pin("p1")
        self.assertIsNotNone(tek)
        ring.set_pin("p1", tek, "4711")
        self.assertTrue(ring.has_pin("p1"))
        self.assertIsNone(ring.tek_without_pin("p1"))
        self.assertEqual(ring.tek_with_pin("p1", "4711"), tek)
        with self.assertRaises(K.CryptoError):
            ring.tek_with_pin("p1", "0000")
        # Persistenz
        ring2 = K.Keyring(ring.to_dict())
        self.assertEqual(ring2.dek("p1"), dek)
        self.assertEqual(ring2.tek_with_pin("p1", "4711"), tek)
        # Master-Schlüssel allein reicht nicht für den Textschlüssel
        self.assertNotIn(tek.decode(), str(ring2.to_dict()))
        # PIN entfernen
        ring2.remove_pin("p1", tek)
        self.assertEqual(ring2.tek_without_pin("p1"), tek)

    def test_reset_pin_new_text_key(self):
        ring = K.Keyring()
        ring.ensure_person("p1")
        tek = ring.tek_without_pin("p1")
        ring.set_pin("p1", tek, "1234")
        ring.reset_pin("p1")
        self.assertFalse(ring.has_pin("p1"))
        self.assertNotEqual(ring.tek_without_pin("p1"), tek)
        self.assertEqual(ring.tek_gen("p1"), 1)

    def test_admin_secret(self):
        h = K.hash_secret("2468")
        self.assertTrue(K.verify_secret("2468", h))
        self.assertFalse(K.verify_secret("2469", h))
        self.assertFalse(K.verify_secret("2468", None))


if __name__ == "__main__":
    unittest.main()
