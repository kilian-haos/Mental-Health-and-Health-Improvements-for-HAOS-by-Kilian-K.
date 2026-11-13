"""Brain dump: a personal to-do / thought list with up to three levels (pure Python).

Item: {"id", "text", "done", "created", "done_at", "children": [...]}
Rules:
* at most 3 levels (item -> sub-item -> sub-sub-item),
* ticking or unticking an item applies the same state to all of its sub-items,
* nothing is ever deleted implicitly – deleting is an explicit action (removes the sub-tree).
Stored encrypted with the person's text key (like the journal).
"""
from __future__ import annotations

import uuid
from typing import Any

MAX_DEPTH = 3
MAX_TEXT = 300
MAX_ITEMS = 2000


class DumpError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _id() -> str:
    return uuid.uuid4().hex[:10]


def clean_text(text: Any) -> str:
    return " ".join(str(text or "").split())[:MAX_TEXT]


def new_item(text: str, now: str, done: bool = False) -> dict:
    t = clean_text(text)
    if not t:
        raise DumpError("empty")
    return {"id": _id(), "text": t, "done": bool(done), "created": now, "done_at": now if done else None, "children": []}


def normalize(items: Any, depth: int = 1, seen: set[str] | None = None) -> list[dict]:
    """Repair stored data (unknown keys dropped, depth limited, ids unique across the tree)."""
    out = []
    seen = set() if seen is None else seen
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        text = clean_text(it.get("text"))
        if not text:
            continue
        iid = str(it.get("id") or _id())[:20]
        if iid in seen:
            iid = _id()
        seen.add(iid)
        node = {"id": iid, "text": text, "done": bool(it.get("done")), "created": it.get("created"),
                "done_at": it.get("done_at"), "children": []}
        if depth < MAX_DEPTH:
            node["children"] = normalize(it.get("children"), depth + 1, seen)
        out.append(node)
    return out


def walk(items: list[dict], depth: int = 1, parent: dict | None = None):
    """Yield (node, siblings_list, depth, parent) for every node."""
    for it in items:
        yield it, items, depth, parent
        yield from walk(it["children"], depth + 1, it)


def count(items: list[dict]) -> int:
    return sum(1 for _ in walk(items))


def find(items: list[dict], iid: str) -> tuple[dict, list[dict], int, dict | None]:
    for node, sibs, depth, parent in walk(items):
        if node["id"] == iid:
            return node, sibs, depth, parent
    raise DumpError("not_found")


def height(node: dict) -> int:
    """Levels in this sub-tree (a leaf has height 1)."""
    return 1 + max((height(c) for c in node["children"]), default=0)


def add(items: list[dict], texts: list[str], now: str, parent_id: str | None = None, done: list[bool] | None = None) -> list[dict]:
    """Add one or more items (top level or below `parent_id`). Returns the new items."""
    if parent_id:
        parent, _, depth, _ = find(items, parent_id)
        if depth >= MAX_DEPTH:
            raise DumpError("too_deep")
        target = parent["children"]
    else:
        target = items
    new = []
    for k, t in enumerate(texts):
        if not clean_text(t):
            continue
        if count(items) + len(new) >= MAX_ITEMS:
            raise DumpError("too_many")
        new.append(new_item(t, now, bool(done[k]) if done and k < len(done) else False))
    target.extend(new)
    return new


def set_done(items: list[dict], iid: str, done: bool, now: str) -> dict:
    """Tick/untick an item – the same state goes to all of its sub-items."""
    node, _, _, _ = find(items, iid)
    for n, _, _, _ in walk([node]):
        n["done"] = bool(done)
        n["done_at"] = now if done else None
    return node


def edit(items: list[dict], iid: str, text: str) -> dict:
    node, _, _, _ = find(items, iid)
    t = clean_text(text)
    if not t:
        raise DumpError("empty")
    node["text"] = t
    return node


def delete(items: list[dict], iid: str) -> int:
    node, sibs, _, _ = find(items, iid)
    n = count([node])
    sibs.remove(node)
    return n


def move(items: list[dict], iid: str, parent_id: str | None, index: int) -> None:
    """Move an item (with its sub-items) to another parent and/or position."""
    node, sibs, _, _ = find(items, iid)
    if parent_id:
        if parent_id == iid or any(n["id"] == parent_id for n, _, _, _ in walk(node["children"])):
            raise DumpError("into_itself")
        parent, _, pdepth, _ = find(items, parent_id)
        if pdepth + height(node) > MAX_DEPTH:
            raise DumpError("too_deep")
        target = parent["children"]
    else:
        target = items
    old_index = sibs.index(node)
    sibs.remove(node)
    if target is sibs and index > old_index:
        index -= 1
    index = max(0, min(len(target), int(index)))
    target.insert(index, node)


def step(items: list[dict], iid: str, direction: str) -> None:
    """Small sorting steps for touch: up / down / indent (into previous sibling) / outdent."""
    node, sibs, depth, parent = find(items, iid)
    i = sibs.index(node)
    if direction == "up" and i > 0:
        sibs[i - 1], sibs[i] = sibs[i], sibs[i - 1]
    elif direction == "down" and i < len(sibs) - 1:
        sibs[i + 1], sibs[i] = sibs[i], sibs[i + 1]
    elif direction == "indent" and i > 0:
        move(items, iid, sibs[i - 1]["id"], len(sibs[i - 1]["children"]))
    elif direction == "outdent" and parent is not None:
        _, psibs, _, _ = find(items, parent["id"])
        move(items, iid, None if depth == 2 else _parent_id(items, parent["id"]), psibs.index(parent) + 1)


def _parent_id(items: list[dict], iid: str) -> str | None:
    _, _, _, parent = find(items, iid)
    return parent["id"] if parent else None


def open_items(items: list[dict]) -> list[dict]:
    """Top-level items that are not done (with their sub-items) – for ticking off in the evening."""
    return [it for it in items if not it["done"]]


def preview(items: list[dict]) -> dict:
    """The two oldest and the two newest open top-level items (collapsed), plus counters."""
    open_ = [it for it in items if not it["done"]]
    by_age = sorted(open_, key=lambda it: it.get("created") or "")
    oldest = by_age[:2]
    newest = [it for it in reversed(by_age[2:]) if it not in oldest][:2]

    def brief(it: dict) -> dict:
        sub = [n for n, _, _, _ in walk(it["children"])]
        return {"id": it["id"], "text": it["text"], "created": it.get("created"),
                "sub": len(sub), "sub_done": sum(1 for n in sub if n["done"])}
    total = count(items)
    done = sum(1 for n, _, _, _ in walk(items) if n["done"])
    return {"oldest": [brief(i) for i in oldest], "newest": [brief(i) for i in newest],
            "open": len(open_), "total": total, "done": done}
