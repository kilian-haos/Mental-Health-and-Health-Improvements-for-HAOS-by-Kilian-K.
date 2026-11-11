"""Text analysis of one's own entries, German + English (pure Python, no external packages).

Topics via keywords, simple stems and synonym lists plus learned frequent terms; a lexicon
based tone; links between topics and mood ("what does you good" / "what drags you down").
"""
from __future__ import annotations

import re
import statistics
import unicodedata
from collections import Counter

_WORD = re.compile(r"[\wäöüß]+", re.UNICODE)

STOP = set("""
a an and are as at be been but by for from had has have he her his i if in into is it its just me my of on or our so
than that the their them then there these they this to too us was we were what when which who will with you your
im am all also can could did do does done get got its i'm i've dont don't very really much more some any one
aber als am an auch auf aus bei bin bis bist da damit dann das dass dein dem den der des die dies diese doch dort du
durch ein eine einem einen einer eines er es etwas euch für gegen hab habe haben hat hatte hätte ich ihr im in ins
ist ja jetzt kann man mehr mein mich mir mit muss nach nicht noch nun nur ob oder schon sehr sein sich sie sind so
um und uns unter viel vom von vor war waren was weil wenn wer wie wieder wir wird zu zum zur über heute gestern
morgen mal ganz gar eigentlich irgendwie halt einfach immer
""".split())

NEGATIONS = {"nicht", "kein", "keine", "keinen", "keiner", "nie", "niemals", "ohne", "not", "no", "never", "without",
             "nothing", "nichts", "don't", "didn't", "wasn't", "isn't"}

# Themen: kanonischer Schlüssel -> Wörter (Stämme werden automatisch gebildet), de + en
TOPICS: dict[str, tuple[str, ...]] = {
    "family": ("familie", "family", "mama", "papa", "mutter", "vater", "eltern", "bruder", "schwester", "geschwister",
               "oma", "opa", "kinder", "kind", "sohn", "tochter", "mom", "mum", "dad", "parents", "brother", "sister",
               "grandma", "grandpa", "kids", "son", "daughter"),
    "friends": ("freund", "freunde", "freundin", "kumpel", "clique", "friend", "friends", "mates", "buddy", "treffen",
                "meet", "hangout"),
    "partner": ("partner", "partnerin", "freund", "date", "liebe", "love", "beziehung", "relationship", "schatz", "kuss"),
    "work": ("arbeit", "job", "büro", "chef", "chefin", "kollege", "kollegin", "meeting", "projekt", "kunde", "schicht",
             "work", "office", "boss", "colleague", "project", "client", "shift", "deadline"),
    "school": ("schule", "klasse", "lehrer", "lehrerin", "hausaufgaben", "test", "klausur", "prüfung", "unterricht",
               "uni", "studium", "vorlesung", "school", "teacher", "homework", "exam", "class", "lecture", "university"),
    "sport": ("sport", "training", "fitness", "gym", "joggen", "laufen", "rennen", "radfahren", "fahrrad", "schwimmen",
              "fußball", "yoga", "workout", "run", "running", "cycling", "swim", "football", "soccer", "basketball"),
    "nature": ("spaziergang", "spazieren", "wald", "natur", "park", "draußen", "wandern", "berge", "see", "sonne",
               "walk", "forest", "nature", "outside", "outdoors", "hike", "hiking", "mountains", "lake", "sun", "garten",
               "garden"),
    "sleep": ("schlaf", "schlafen", "müde", "ausgeschlafen", "nickerchen", "sleep", "tired", "nap", "rested", "insomnia"),
    "food": ("essen", "kochen", "pizza", "frühstück", "abendessen", "restaurant", "lecker", "food", "cook", "cooking",
             "dinner", "lunch", "breakfast", "tasty", "meal"),
    "illness": ("krank", "erkältet", "erkältung", "fieber", "kopfschmerzen", "schmerzen", "arzt", "ärztin", "grippe",
                "sick", "ill", "cold", "fever", "headache", "pain", "doctor", "flu"),
    "stress": ("stress", "gestresst", "druck", "hektik", "überfordert", "streit", "nervig", "stressed", "pressure",
               "overwhelmed", "rush", "busy", "anxious", "angst", "sorgen", "worry", "worries"),
    "conflict": ("streit", "gestritten", "ärger", "wütend", "konflikt", "argument", "fight", "angry", "conflict", "mad"),
    "music": ("musik", "konzert", "singen", "gitarre", "klavier", "song", "music", "concert", "sing", "guitar", "piano",
              "band", "chor", "choir"),
    "games": ("zocken", "spielen", "spiel", "playstation", "konsole", "gaming", "game", "games", "videospiel"),
    "screen": ("handy", "social", "instagram", "tiktok", "youtube", "serie", "netflix", "phone", "series", "tv",
               "fernsehen", "film", "movie"),
    "pets": ("hund", "katze", "pferd", "haustier", "dog", "cat", "horse", "pet", "puppy", "kitten"),
    "rest": ("entspannt", "entspannen", "ruhe", "chillen", "ausruhen", "pause", "relaxed", "relax", "calm", "rest",
             "chill", "lesen", "buch", "read", "book", "bad", "bath", "sauna"),
    "achievement": ("geschafft", "erfolg", "stolz", "gewonnen", "bestanden", "fertig", "erledigt", "achieved", "success",
                    "proud", "won", "passed", "finished", "done"),
    "learning": ("lernen", "gelernt", "kurs", "neues", "learn", "learned", "course"),
    "creative": ("malen", "zeichnen", "basteln", "bauen", "schreiben", "fotografieren", "draw", "paint", "craft", "build",
                 "write", "photography", "creative", "kreativ"),
    "travel": ("urlaub", "reise", "ausflug", "ferien", "trip", "holiday", "vacation", "travel", "journey"),
    "money": ("geld", "rechnung", "kosten", "teuer", "money", "bill", "expensive", "cost", "rent", "miete"),
    "weather": ("regen", "regnerisch", "kalt", "schnee", "sonnig", "warm", "rain", "rainy", "snow", "sunny", "grau",
                "grey", "gray"),
}

POSITIVE = {
    "gut": 1.0, "super": 1.5, "toll": 1.5, "schön": 1.2, "glücklich": 1.8, "froh": 1.3, "zufrieden": 1.2, "lustig": 1.2,
    "spaß": 1.4, "gelacht": 1.4, "lachen": 1.2, "entspannt": 1.1, "stolz": 1.3, "dankbar": 1.5, "liebe": 1.3, "genial": 1.5,
    "perfekt": 1.5, "erfolgreich": 1.3, "geschafft": 1.2, "freude": 1.5, "gefreut": 1.3, "wunderbar": 1.6, "angenehm": 1.0,
    "ruhig": 0.6, "motiviert": 1.2, "erholt": 1.2, "ausgeschlafen": 1.0, "lecker": 0.8, "witzig": 1.1, "herrlich": 1.4,
    "good": 1.0, "great": 1.5, "nice": 1.0, "happy": 1.8, "glad": 1.2, "fun": 1.4, "laughed": 1.4, "relaxed": 1.1,
    "proud": 1.3, "grateful": 1.5, "love": 1.3, "loved": 1.3, "awesome": 1.6, "amazing": 1.6, "wonderful": 1.6,
    "perfect": 1.5, "calm": 0.6, "motivated": 1.2, "rested": 1.0, "enjoyed": 1.3, "excited": 1.3, "beautiful": 1.2,
}
NEGATIVE = {
    "schlecht": 1.2, "traurig": 1.6, "müde": 0.8, "erschöpft": 1.3, "gestresst": 1.3, "stress": 1.0, "wütend": 1.4,
    "ärger": 1.2, "geärgert": 1.2, "streit": 1.3, "angst": 1.4, "sorgen": 1.1, "einsam": 1.6, "allein": 0.8, "krank": 1.1,
    "schmerzen": 1.1, "nervig": 1.0, "genervt": 1.1, "frustriert": 1.3, "enttäuscht": 1.3, "überfordert": 1.4,
    "schlimm": 1.4, "doof": 0.8, "blöd": 0.8, "mies": 1.2, "kaputt": 1.0, "weinen": 1.4, "geweint": 1.5, "hass": 1.6,
    "langweilig": 0.7, "unruhig": 0.9, "kopfschmerzen": 1.0, "zoff": 1.2,
    "bad": 1.2, "sad": 1.6, "tired": 0.8, "exhausted": 1.3, "stressed": 1.3, "angry": 1.4, "annoyed": 1.1, "fight": 1.3,
    "anxious": 1.4, "worried": 1.1, "lonely": 1.6, "alone": 0.8, "sick": 1.1, "pain": 1.1, "frustrated": 1.3,
    "disappointed": 1.3, "overwhelmed": 1.4, "terrible": 1.6, "awful": 1.6, "cried": 1.5, "hate": 1.6, "boring": 0.7,
    "headache": 1.0, "upset": 1.3,
}

_DE_SUFFIX = ("ungen", "heiten", "keiten", "ung", "heit", "keit", "lich", "isch", "ern", "em", "en", "er", "es", "e", "n", "s")
_EN_SUFFIX = ("ingly", "edly", "ing", "ed", "ly", "es", "s")


def fold(s: str) -> str:
    s = s.lower().replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def stem(word: str) -> str:
    w = fold(word)
    if len(w) <= 3:
        return w
    for suf in _EN_SUFFIX + _DE_SUFFIX:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokens(text: str) -> list[str]:
    return [t for t in _WORD.findall((text or "").lower()) if not t.isdigit()]


def content_stems(text: str) -> list[str]:
    return [stem(t) for t in tokens(text) if t not in STOP and len(t) > 2]


_TOPIC_STEMS: dict[str, set[str]] = {k: {stem(w) for w in v} for k, v in TOPICS.items()}
_STEM_TOPICS: dict[str, set[str]] = {}
for _k, _vs in _TOPIC_STEMS.items():
    for _s in _vs:
        _STEM_TOPICS.setdefault(_s, set()).add(_k)
_POS = {stem(k): v for k, v in POSITIVE.items()}
_NEG = {stem(k): v for k, v in NEGATIVE.items()}


def synonyms(st: str) -> set[str]:
    """All stems sharing a topic with `st` (query expansion)."""
    out = {st}
    for t in _STEM_TOPICS.get(st, ()):
        out |= _TOPIC_STEMS[t]
    return out


def topics(text: str) -> set[str]:
    out: set[str] = set()
    for st in content_stems(text):
        out |= _STEM_TOPICS.get(st, set())
    return out


def tone(text: str) -> float | None:
    """-1..+1 lexicon tone with simple negation handling; None if no sentiment words."""
    toks = tokens(text)
    score = 0.0
    hits = 0
    neg_left = 0
    for t in toks:
        if t in NEGATIONS:
            neg_left = 3
            continue
        st = stem(t)
        val = _POS.get(st, 0.0) - _NEG.get(st, 0.0)
        if val:
            if neg_left:
                val = -val * 0.8
            score += val
            hits += 1
        if neg_left:
            neg_left -= 1
    if not hits:
        return None
    return max(-1.0, min(1.0, score / (hits ** 0.5) / 2.0))


def learned_terms(day_texts: dict[str, str], min_days: int = 3, top: int = 20) -> list[dict]:
    """Frequent personal terms that are no known topic (e.g. names of places, hobbies).

    Returns [{"stem", "word", "days"}] – `word` is the most frequent original spelling.
    """
    cnt: Counter = Counter()
    words: dict[str, Counter] = {}
    for txt in day_texts.values():
        seen = set()
        for t in tokens(txt):
            if t in STOP or len(t) <= 2:
                continue
            st = stem(t)
            words.setdefault(st, Counter())[t] += 1
            seen.add(st)
        for st in seen:
            if st not in _STEM_TOPICS and st not in _POS and st not in _NEG and len(st) >= 4:
                cnt[st] += 1
    return [{"stem": w, "word": words[w].most_common(1)[0][0], "days": c} for w, c in cnt.most_common(top) if c >= min_days]


def topic_effects(days: list[tuple[set[str], float]], min_days: int = 3) -> list[dict]:
    """Per topic: mean mood on days with the topic vs. overall. Sorted by effect."""
    if len(days) < 7:
        return []
    overall = statistics.mean(m for _, m in days)
    by: dict[str, list[float]] = {}
    for tps, m in days:
        for t in tps:
            by.setdefault(t, []).append(m)
    out = []
    for t, ms in by.items():
        if len(ms) >= min_days:
            eff = statistics.mean(ms) - overall
            out.append({"topic": t, "effect": round(eff, 2), "days": len(ms)})
    out.sort(key=lambda x: x["effect"], reverse=True)
    return out
