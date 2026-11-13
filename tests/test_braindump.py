"""Brain dump tree: 3 levels, cascade, sorting, preview."""
import unittest

import _path  # noqa: F401
from logic import braindump as B

NOW = "2026-11-13T08:00:00+01:00"


def tree():
    items = []
    a, b = B.add(items, ["Umzug planen", "Steuer"], NOW)
    a1, a2, a3 = B.add(items, ["Kartons", "Helfer fragen", "Ummelden"], NOW, a["id"])
    B.add(items, ["Bürgeramt-Termin"], NOW, a3["id"])
    return items, a, b, a1, a2, a3


class BrainDump(unittest.TestCase):
    def test_add_and_depth_limit(self):
        items, a, b, a1, a2, a3 = tree()
        self.assertEqual(B.count(items), 6)
        deep = a3["children"][0]
        with self.assertRaises(B.DumpError):
            B.add(items, ["vierte Ebene"], NOW, deep["id"])
        self.assertEqual(B.add(items, ["  ", ""], NOW), [])
        with self.assertRaises(B.DumpError):
            B.new_item("   ", NOW)

    def test_cascade_done(self):
        items, a, *_ = tree()
        B.set_done(items, a["id"], True, NOW)
        self.assertTrue(all(n["done"] for n, *_ in B.walk([a])))
        B.set_done(items, a["id"], False, NOW)
        self.assertFalse(any(n["done"] for n, *_ in B.walk([a])))

    def test_sub_toggle_independent(self):
        items, a, b, a1, a2, a3 = tree()
        B.set_done(items, a3["id"], True, NOW)
        self.assertTrue(a3["children"][0]["done"])
        self.assertFalse(a["done"])
        self.assertFalse(a1["done"])

    def test_delete_subtree(self):
        items, a, *_ = tree()
        self.assertEqual(B.delete(items, a["id"]), 5)
        self.assertEqual(B.count(items), 1)

    def test_move_and_depth_rules(self):
        items, a, b, a1, a2, a3 = tree()
        with self.assertRaises(B.DumpError):
            B.move(items, a["id"], a3["id"], 0)          # in sich selbst
        with self.assertRaises(B.DumpError):
            B.move(items, a3["id"], a1["id"], 0)         # würde 4 Ebenen ergeben
        B.move(items, b["id"], a["id"], 0)                # Steuer unter Umzug
        self.assertEqual(a["children"][0]["id"], b["id"])
        B.move(items, b["id"], None, 0)
        self.assertEqual(items[0]["id"], b["id"])

    def test_steps(self):
        items, a, b, a1, a2, a3 = tree()
        B.step(items, b["id"], "up")
        self.assertEqual(items[0]["id"], b["id"])
        B.step(items, a2["id"], "indent")                # unter Kartons
        self.assertEqual(a1["children"][0]["id"], a2["id"])
        B.step(items, a2["id"], "outdent")
        self.assertIn(a2["id"], [c["id"] for c in a["children"]])
        B.step(items, a1["id"], "outdent")               # auf oberste Ebene
        self.assertIn(a1["id"], [i["id"] for i in items])

    def test_preview_oldest_newest(self):
        items = []
        for k in range(6):
            B.add(items, [f"Punkt {k}"], f"2026-11-0{k + 1}T08:00:00")
        B.set_done(items, items[0]["id"], True, NOW)
        pv = B.preview(items)
        self.assertEqual([x["text"] for x in pv["oldest"]], ["Punkt 1", "Punkt 2"])
        self.assertEqual([x["text"] for x in pv["newest"]], ["Punkt 5", "Punkt 4"])
        self.assertEqual((pv["open"], pv["total"], pv["done"]), (5, 6, 1))

    def test_normalize(self):
        raw = [{"id": "x", "text": "A", "children": [{"id": "x", "text": "B", "children": [{"text": "C", "children": [{"text": "D"}]}]}]}, "junk", {"text": ""}]
        items = B.normalize(raw)
        self.assertEqual(B.count(items), 3)                # D (4. Ebene) fällt weg
        ids = [n["id"] for n, *_ in B.walk(items)]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
