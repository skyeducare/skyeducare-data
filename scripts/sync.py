#!/usr/bin/env python3
"""
SKY EDUCARE - अपने आप डेटा अपडेट (GitHub Actions से हर 5 मिनट)

1. skyeducare.in (Classplus) से सारे कोर्स, दाम, छूट लाता है।
   - पुराना कोर्स: टीचर, कैटेगरी, बैज वैसे ही रहते हैं, सिर्फ़ नाम/दाम/विवरण अपडेट होते हैं।
   - नया कोर्स: नियमों से अपने आप टीचर, कैटेगरी और बैज तय होते हैं।
   - Classplus से हटाया गया कोर्स वेबसाइट से भी हट जाता है।
2. YouTube चैनल @SkyEducare (RSS) से नए वीडियो लाता है और हर वीडियो को
   सही टीचर और उसी विषय के असली कोर्स से जोड़ता है।
3. overrides.json में लिखे हाथ के बदलाव सबसे आख़िर में लागू होते हैं।
4. data/live-data.json लिखता है, जिसे वेबसाइट हर बार खुलते समय पढ़ती है।

फ़ाइल तभी बदलती है जब असली डेटा बदले, इसलिए बेकार commit नहीं बनते।
"""

import datetime
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
COURSES_FILE = os.path.join(DATA, "courses.json")
BLOGS_FILE = os.path.join(DATA, "blogs.json")
LIVE_FILE = os.path.join(DATA, "live-data.json")
STATUS_FILE = os.path.join(DATA, "status.json")
OVERRIDES_FILE = os.path.join(ROOT, "overrides.json")

CLASSPLUS_URL = ("https://api.classplusapp.com/v2/course/preview/similar/"
                 "eyJ0dXRvcklkIjpudWxsLCJvcmdJZCI6ODcyNSwiY2F0ZWdvcnlJZCI6bnVsbH0="
                 "?filterId=[1]&sortId=[7]&subCatList=&mainCategory=0&limit={limit}&offset={offset}")
CHANNEL_ID = "UC68B2m3VvtM10QqpgUeVOxw"
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL_ID
MAX_BLOGS = 60
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

FACULTY = {
    "ashok": "Ashok Jangir Sir (NET - English, RPSC Lecturer)",
    "sahil": "Dr. Sahil Gurjar Sir (Ph.D, NET-JRF, Hindi Subject Head)",
    "rajendra": "Rajendra Rajpurohit Sir (NET - Political Science)",
    "katariya": "S.K. KATARIYA Sir (Director & Founder, Teaching Methods Author)",
    "leeladhar": "Leeladhar Parjapat Sir (Subject Expert)",
    "jakhar": "Dr. Jakhar Sir (Veterinary Expert)",
    "yashwardhan": "Yashwardhan Shekhawat Sir (B.Tech - Mathematics Expert)",
}

DEFAULT_FEATURES = [
    "राजस्थान लोक सेवा आयोग (RPSC) के नवीनतम परीक्षा पैटर्न पर आधारित।",
    "विशेषज्ञ शिक्षकों द्वारा अवधारणाओं को सरल और सुगम बनाने वाली कक्षाएं।",
    "100% प्रिंटेबल पैनल पीडीएफ ई-नोट्स (प्रिंटिंग की पूर्ण सुविधा सहित)।",
    "नियमित अभ्यास व प्रदर्शन विश्लेषण हेतु विषयवार टेस्ट और क्विज़।",
    "Android App, iOS App एवं वेब पोर्टल पर निर्बाध अध्ययन सुविधा।",
]


def log(msg):
    print(msg, flush=True)


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    """लिखता है और बताता है कि फ़ाइल सच में बदली या नहीं।"""
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    old = None
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            old = f.read()
    if old == text:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def http_get(url, headers=None, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read()
        except Exception as e:  # नेटवर्क की छोटी गड़बड़ी पर दोबारा कोशिश
            last = e
            time.sleep(2 * (i + 1))
    raise last


def has(text, words):
    return any(w in text for w in words)


def word(text, w):
    return re.search(r"(?<![a-z])" + w + r"(?![a-z])", text) is not None


# ---------------------------------------------------------------- कोर्स के नियम
def determine_faculty(title, desc):
    tt = (title or "").lower()
    t = (tt + " " + (desc or "").lower())
    if has(t, ["sk katariya", "katariya"]) or has(tt, ["शिक्षण विधियाँ", "शिक्षण विधि", "teaching method", "sanskrit"]):
        return FACULTY["katariya"]
    if has(tt, ["avfo", "veterinary", "पशुपालन", "पशु "]) or "jakhar" in t:
        return FACULTY["jakhar"]
    if has(tt, ["ldc", "math", "गणित", "arithmetic", "shekhawat", "yashwardhan"]):
        return FACULTY["yashwardhan"]
    if has(tt, ["english", "अंग्रेज़ी", "अंग्रेजी", "angrezi"]) or "ashok" in t:
        return FACULTY["ashok"]
    if word(tt, "eo") or word(tt, "ro") or has(tt, ["nagar palika", "नगरपालिका", "polity", "राजव्यवस्था", "संविधान", "constitution"]) \
            or has(t, ["rajendra", "rajpurohit", "राजपुरोहित"]):
        return FACULTY["rajendra"]
    if has(tt, ["hindi", "हिंदी", "हिन्दी"]) or "sahil" in t:
        return FACULTY["sahil"]
    if has(tt, ["gk", "current affairs", "करंट", "geography", "history", "इतिहास", "भूगोल"]) or "leeladhar" in t:
        return FACULTY["leeladhar"]
    if has(tt, ["reet", "रीट", "पात्रता"]):
        return FACULTY["yashwardhan"]
    # शीर्षक से पता न चले तो पूरे विवरण से
    if has(t, ["english", "अंग्रेज़ी"]):
        return FACULTY["ashok"]
    if has(t, ["hindi", "हिंदी"]):
        return FACULTY["sahil"]
    if has(t, ["polity", "संविधान"]):
        return FACULTY["rajendra"]
    if has(t, ["math", "गणित"]):
        return FACULTY["yashwardhan"]
    if has(t, ["history", "इतिहास", "current affairs"]):
        return FACULTY["leeladhar"]
    return FACULTY["katariya"]


def determine_badge_and_categories(title):
    t = (title or "").lower()
    cats = ["all"]
    if "live" in t:
        badge, header = "LIVE BATCH", "header-live"
        cats.append("live")
    elif "test" in t:
        badge, header = "TEST SERIES", "header-test"
        cats += ["test", "tests"]
    elif has(t, ["pdf", "notes", "पुस्तक", "नोट्स"]):
        badge, header = "PANEL NOTES / PDF", "header-notes"
        cats.append("notes")
    else:
        badge, header = "RECORDED BATCH", "header-rec"
        cats.append("recorded")
    if has(t, ["1st grade", "1st + 2nd", "प्रथम श्रेणी", "school lecturer", "1st paper"]):
        cats.append("1st-grade")
    if has(t, ["2nd grade", "+ 2nd", "द्वितीय श्रेणी", "senior teacher"]):
        cats.append("2nd-grade")
    if has(t, ["reet", "रीट", "3rd grade", "पात्रता"]):
        cats += ["reet", "3rd-grade"]
    if word(t, "eo") or word(t, "ro"):
        cats += ["eo-ro", "eoro"]
    if has(t, ["gk", "current affairs", "करंट"]):
        cats.append("gk")
    if has(t, ["english", "अंग्रेजी", "अंग्रेज़ी"]):
        cats.append("english")
    if has(t, ["hindi", "हिंदी", "हिन्दी"]):
        cats.append("hindi")
    if has(t, ["avfo", "veterinary"]):
        cats.append("avfo")
    out = []
    for c in cats:
        if c not in out:
            out.append(c)
    return badge, header, sorted(out)


def extract_features(desc):
    feats = []
    for line in (desc or "").split("\n"):
        c = re.sub(r"^[✔✅•\-\*📖🎥📝📊💬📱⭐✍️🏢🗣️📞🚚🔒🎯📘📗🏙️🎓📚✨📅\s]+", "", line.strip()).strip()
        if len(c) > 12 and not re.match(r"^(contact|helpline|संपर्क)", c, re.I) and c not in feats and len(feats) < 7:
            feats.append(c)
    return feats or list(DEFAULT_FEATURES)


def validity_of(desc):
    d = (desc or "").lower()
    if "18 month" in d or "18 माह" in d:
        return "18 Month Validity"
    if "2 year" in d or "2 वर्ष" in d:
        return "2 Year Validity"
    if "till exam" in d or "परीक्षा तक" in d:
        return "Till Exam Date"
    return "1 Year Validity"


def short_desc_of(title, desc):
    lines = [l.strip() for l in (desc or "").split("\n") if len(l.strip()) > 20 and not l.strip().startswith("🎯")]
    s = lines[0] if lines else f"{title} हेतु आरपीएससी नवीनतम सिलेबस आधारित संपूर्ण ऑनलाइन कोर्स।"
    return s if len(s) <= 160 else s[:157] + "..."


def rupee(n):
    return "₹" + f"{int(round(n)):,}"


def learning_stats(res):
    if not isinstance(res, dict):
        return None
    parts = []
    v, f, t = res.get("videos") or 0, res.get("files") or 0, res.get("tests") or 0
    if v:
        parts.append(f"{v} Videos")
    if f:
        parts.append(f"{f} PDFs")
    if t:
        parts.append(f"{t} Tests")
    return ", ".join(parts) if parts else None


def fetch_classplus():
    all_courses, offset, total = [], 0, None
    while True:
        raw = http_get(CLASSPLUS_URL.format(limit=50, offset=offset), {"Accept": "application/json", "Api-Version": "22"})
        j = json.loads(raw.decode("utf-8"))
        data = (j or {}).get("data") or {}
        batch = data.get("coursesData") or []
        if total is None:
            try:
                total = int(data.get("totalCount"))
            except Exception:
                total = None
        all_courses += batch
        offset += 50
        if not batch or len(batch) < 50 or (total is not None and len(all_courses) >= total) or offset > 1000:
            break
    return all_courses, total


def sync_courses(old_courses):
    raw, total = fetch_classplus()
    raw = [c for c in raw if str(c.get("isPublished", 1)) != "0"]
    log(f"Classplus: {len(raw)} published courses (totalCount={total})")
    if not raw:
        raise RuntimeError("Classplus returned 0 courses")
    if old_courses and len(raw) < 0.5 * len(old_courses):
        raise RuntimeError(f"Classplus returned only {len(raw)} courses (earlier {len(old_courses)}). Keeping old data for safety.")

    old_by_code = {str(c.get("code")): c for c in old_courses}
    out, added, changed, removed = [], [], [], []
    for idx, c in enumerate(raw, start=1):
        code = str(c.get("id"))
        title = (c.get("name") or "").strip()
        orig = float(c.get("price") or 0)
        disc = float(c.get("discount") or 0)
        sell = max(0.0, orig - disc)
        pct = round(disc / orig * 100) if orig > 0 and disc > 0 else 0
        desc = c.get("description") or c.get("courseDescription") or ""
        fields = {
            "code": code,
            "title": title,
            "price": rupee(sell),
            "originalPrice": rupee(orig) if orig > sell else "",
            "discount": f"{pct}% OFF" if pct > 0 else "SPECIAL PRICE",
            "rawDescription": desc,
        }
        if c.get("imageUrl"):
            fields["imageUrl"] = c["imageUrl"]
        old = old_by_code.get(code)
        if old:
            course = dict(old)
            before = json.dumps([course.get(k) for k in ("title", "price", "originalPrice", "discount", "rawDescription")], ensure_ascii=False)
            desc_changed = (course.get("rawDescription") or "") != desc
            course.update(fields)
            if desc_changed:
                course["features"] = extract_features(desc)
                course["shortDesc"] = short_desc_of(title, desc)
                course["validity"] = validity_of(desc)
            after = json.dumps([course.get(k) for k in ("title", "price", "originalPrice", "discount", "rawDescription")], ensure_ascii=False)
            if before != after:
                changed.append(title)
        else:
            badge, header, cats = determine_badge_and_categories(title)
            course = {
                "id": 0,
                "code": code,
                "title": title,
                "badge": badge,
                "headerClass": header,
                "price": fields["price"],
                "originalPrice": fields["originalPrice"],
                "discount": fields["discount"],
                "validity": validity_of(desc),
                "faculty": determine_faculty(title, desc),
                "learningStats": learning_stats(c.get("resources")) or "Videos, PDFs & Mock Tests",
                "categories": cats,
                "tags": ["CLASSES", "PDF NOTES", "TEST SERIES"],
                "shortDesc": short_desc_of(title, desc),
                "rawDescription": desc,
                "features": extract_features(desc),
                "autoAdded": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
            }
            if fields.get("imageUrl"):
                course["imageUrl"] = fields["imageUrl"]
            added.append(f"{title} -> {course['faculty']} / {', '.join(cats)}")
        course["id"] = idx
        out.append(course)
    seen = {str(c.get("id")) for c in raw}
    removed = [c.get("title") for c in old_courses if str(c.get("code")) not in seen]
    return out, added, changed, removed


# ---------------------------------------------------------------- YouTube
VIDEO_RULES = [
    # (शब्द, टीचर key, कैटेगरी)
    (["शिक्षण विधि", "teaching method", "pedagogy", "sanskrit", "संस्कृत", "katariya"], "katariya", "Teaching Methods & Pedagogy"),
    (["hindi", "हिन्दी", "हिंदी", "बालकाण्ड", "साहित्य", "व्याकरण", "रामचरितमानस", "sahil"], "sahil", "RPSC Hindi Special"),
    (["english", "noun", "speech", "tense", "grammar", "ashok jangir", "literature"], "ashok", "RPSC English Special"),
    (["polity", "संविधान", "राजव्यवस्था", "eo/ro", "eo ro", "eo / ro", "rajpurohit", "नगरपालिका"], "rajendra", "Polity & EO/RO"),
    (["avfo", "veterinary", "पशुपालन", "पशु ", "jakhar"], "jakhar", "Veterinary & Animal Husbandry"),
    (["math", "गणित", "प्रतिशत", "percentage", "reet", "ldc", "science", "विज्ञान"], "yashwardhan", "REET Science & Math"),
    (["history", "इतिहास", "gk", "current affairs", "करंट", "geography", "भूगोल", "leeladhar"], "leeladhar", "GK & Current Affairs"),
]

STOP = {"the", "and", "for", "new", "part", "live", "class", "batch", "rpsc", "sir", "with", "from", "भाग", "के", "की", "का", "एवं", "और"}


def tokens(s):
    return {w for w in re.split(r"[^0-9a-zA-Zऀ-ॿ]+", (s or "").lower()) if len(w) > 1 and w not in STOP}


def best_course_for(title, faculty, courses):
    tt = tokens(title)
    cands = [c for c in courses if c.get("faculty") == faculty] or courses
    best, score = None, -1.0
    tl = title.lower()
    for c in cands:
        ct = tokens(c.get("title"))
        s = len(tt & ct)
        # परीक्षा का स्तर मिले तो ज़्यादा अंक
        for key in ("1st grade", "2nd grade", "reet", "eo", "avfo", "ldc", "level-1", "level - 1", "level-2", "level 2"):
            if key in tl and key in (c.get("title") or "").lower():
                s += 2
        if "live" in tl and "live" in (c.get("title") or "").lower():
            s += 1
        if c.get("badge") == "PANEL NOTES / PDF" and not has(tl, ["pdf", "notes", "नोट्स"]):
            s -= 0.5
        if s > score:
            best, score = c, s
    return best


def fetch_youtube():
    raw = http_get(RSS_URL)
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
          "media": "http://search.yahoo.com/mrss/"}
    items = []
    for e in root.findall("atom:entry", ns):
        vid = e.find("yt:videoId", ns).text
        title = (e.find("atom:title", ns).text or "").strip()
        pub = e.find("atom:published", ns).text
        link = e.find("atom:link", ns)
        href = link.get("href") if link is not None else ""
        d = e.find(".//media:description", ns)
        items.append({"id": vid, "title": title, "published": pub, "desc": (d.text if d is not None else "") or "",
                      "isShort": "/shorts/" in (href or "")})
    return items


def fetch_stream_ids():
    """चैनल के Live टैब से लाइव क्लास वाले वीडियो की id (RSS में यह जानकारी नहीं होती)।"""
    try:
        html = http_get("https://www.youtube.com/channel/" + CHANNEL_ID + "/streams",
                        {"Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+1"}, tries=2).decode("utf-8", "ignore")
        return set(re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html))
    except Exception as e:
        log(f"(streams page not read: {e})")
        return set()


def build_blog(v, courses):
    title = v["title"]
    tl = title.lower()
    vtype = "recorded"
    if v.get("isShort") or "#shorts" in tl or "#short" in tl:
        vtype = "short"
    elif v.get("isLive") or "live" in tl or "मैराथन" in tl or "मराथन" in tl:
        vtype = "live"
    fac_key, category = None, "Competitive Exams"
    for words, key, cat in VIDEO_RULES:
        if has(tl, words):
            fac_key, category = key, cat
            break
    faculty = FACULTY[fac_key] if fac_key else FACULTY["katariya"]
    course = best_course_for(title, faculty, courses) if courses else None
    try:
        date_str = datetime.datetime.fromisoformat(v["published"].replace("Z", "+00:00")).strftime("%b %d, %Y")
    except Exception:
        date_str = "Recently"
    desc_line = next((l.strip() for l in (v.get("desc") or "").split("\n") if len(l.strip()) > 30 and "http" not in l), "")
    summary = (desc_line[:217] + "...") if len(desc_line) > 220 else desc_line
    if not summary:
        summary = f"इस वीडियो लेक्चर में {faculty.split(' (')[0]} द्वारा '{title}' विषय पर परीक्षा उपयोगी व्याख्या, ट्रिक्स एवं महत्वपूर्ण प्रश्न।"
    return {
        "id": v["id"],
        "title": title,
        "date": date_str,
        "publishedAt": v.get("published"),
        "type": vtype,
        "faculty": faculty,
        "category": category,
        "summary": summary,
        "notes": [
            "लेक्चर के मुख्य संप्रत्यय (Core Concepts) एवं नियम स्पष्टीकरण।",
            "परीक्षा हॉल में समय प्रबंधन एवं सटीक उत्तर चयन की विशेष तकनीक।",
            "SKY EDUCARE मोबाइल ऐप एवं पोर्टल पर उपलब्ध पैनल PDF एवं टेस्ट सीरीज।",
        ],
        "courseCode": str(course["code"]) if course else "",
        "courseTitle": course["title"] if course else "",
    }


def sync_blogs(old_blogs, courses):
    vids = fetch_youtube()
    log(f"YouTube RSS: {len(vids)} videos")
    live_ids = fetch_stream_ids()
    log(f"Live-class ids found: {len(live_ids)}")
    for v in vids:
        if v["id"] in live_ids and not v.get("isShort"):
            v["isLive"] = True
    if not vids:
        raise RuntimeError("YouTube RSS returned 0 videos")
    old_by_id = {b.get("id"): b for b in old_blogs}
    course_codes = {str(c.get("code")) for c in courses}
    fresh, new_ids = [], []
    for v in vids:
        b = build_blog(v, courses)
        old = old_by_id.get(v["id"])
        if old and old.get("manual"):
            b = old  # हाथ से बनाया/सुधारा ब्लॉग वैसा ही रहे
        elif old:
            # पुराने नोट्स/सारांश अच्छे थे तो वही रखें, बस शीर्षक और कोर्स लिंक ताज़ा करें
            keep = dict(old)
            keep["title"] = b["title"]
            keep["publishedAt"] = b["publishedAt"]
            keep["courseCode"], keep["courseTitle"] = b["courseCode"], b["courseTitle"]
            keep["faculty"] = b["faculty"]
            keep["type"] = b["type"]
            b = keep
        else:
            new_ids.append(b["title"])
        fresh.append(b)
    ids = {b["id"] for b in fresh}
    # पुराने वीडियो (जो RSS की 15 वाली सूची से बाहर हो गए) भी रखें, बशर्ते वे असली चैनल के थे
    for b in old_blogs:
        if b.get("id") not in ids and b.get("publishedAt"):
            c = best_course_for(b.get("title", ""), b.get("faculty"), courses) if courses else None
            if c:
                b = dict(b, courseCode=str(c["code"]), courseTitle=c["title"])
            fresh.append(b)
            ids.add(b.get("id"))
    fresh.sort(key=lambda b: b.get("publishedAt") or "", reverse=True)
    return fresh[:MAX_BLOGS], new_ids


# ---------------------------------------------------------------- overrides
def apply_overrides(courses, blogs, ov):
    hide_c = {str(x) for x in ov.get("hideCourses", [])}
    edits = ov.get("courses", {}) or {}
    cs = []
    for c in courses:
        code = str(c.get("code"))
        if code in hide_c:
            continue
        if code in edits and isinstance(edits[code], dict):
            c = dict(c, **edits[code])
        cs.append(c)
    order = [str(x) for x in ov.get("courseOrderFirst", [])]
    if order:
        pos = {code: i for i, code in enumerate(order)}
        cs.sort(key=lambda c: pos.get(str(c.get("code")), len(order)))
    for i, c in enumerate(cs, start=1):
        c["id"] = i
    hide_v = set(ov.get("hideVideos", []))
    vedits = ov.get("videos", {}) or {}
    bs = []
    for b in blogs:
        if b.get("id") in hide_v:
            continue
        if b.get("id") in vedits and isinstance(vedits[b["id"]], dict):
            b = dict(b, **vedits[b["id"]])
        bs.append(b)
    pin = ov.get("pinVideos", [])
    if pin:
        pos = {vid: i for i, vid in enumerate(pin)}
        bs.sort(key=lambda b: pos.get(b.get("id"), len(pin)))
    return cs, bs


RATINGS_FILE = os.path.join(DATA, "ratings.json")
PLAY_URL = "https://play.google.com/store/apps/details?id=co.lynde.ezkzz&hl=en_IN&gl=IN"


def sync_play_rating():
    """Play Store से ऐप की असली रेटिंग, रिव्यू गिनती और डाउनलोड पढ़ता है (वेबसाइट के Testimonials हिस्से के लिए)।"""
    html = http_get(PLAY_URL, {"Accept-Language": "en-IN,en;q=0.9"}).decode("utf-8", "ignore")
    rv = re.search(r'"ratingValue":"?([\d.]+)', html)
    rc = re.search(r'"ratingCount":"?(\d+)', html)
    dl = re.search(r'>([\d,.]+[KMB]?\+)</div><div[^>]*>Downloads', html)
    if not rv or not rc:
        raise RuntimeError("Play Store rating not found")
    play = {"rating": round(float(rv.group(1)), 1), "count": int(rc.group(1)), "downloads": dl.group(1) if dl else None}
    old = load_json(RATINGS_FILE, {})
    if old.get("play") != play:
        old["play"] = play
        old["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_json(RATINGS_FILE, old)
        log(f"Play rating: {play}")
        return True
    return False


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    old_courses = load_json(COURSES_FILE, [])
    old_blogs = load_json(BLOGS_FILE, [])
    status = load_json(STATUS_FILE, {})
    errors = []

    courses = old_courses
    try:
        courses, added, changed, removed = sync_courses(old_courses)
        log(f"Courses: {len(courses)} total, {len(added)} new, {len(changed)} changed, {len(removed)} removed")
        for a in added:
            log("  + " + a)
        for c in changed:
            log("  ~ " + c)
        for r in removed:
            log("  - " + str(r))
    except Exception as e:
        errors.append(f"courses: {e}")
        log(f"!! Course sync failed: {e}")

    blogs = old_blogs
    try:
        blogs, new_v = sync_blogs(old_blogs, courses)
        log(f"Videos: {len(blogs)} kept, {len(new_v)} new")
        for t in new_v:
            log("  + " + t)
    except Exception as e:
        errors.append(f"youtube: {e}")
        log(f"!! YouTube sync failed: {e}")

    try:
        sync_play_rating()
    except Exception as e:  # रेटिंग न मिले तो बाकी सिंक चलता रहे
        log(f"!! Play rating sync failed: {e}")

    c1 = save_json(COURSES_FILE, courses)
    c2 = save_json(BLOGS_FILE, blogs)

    ov = load_json(OVERRIDES_FILE, {})
    live_courses, live_blogs = apply_overrides(json.loads(json.dumps(courses)), json.loads(json.dumps(blogs)), ov)
    live = {"courses": live_courses, "blogs": live_blogs}
    old_live = load_json(LIVE_FILE, {})
    changed_live = {k: old_live.get(k) for k in ("courses", "blogs")} != live
    if changed_live or not old_live.get("updatedAt"):
        live = {"updatedAt": now, "courses": live_courses, "blogs": live_blogs}
        save_json(LIVE_FILE, live)
        log("live-data.json updated")
    else:
        log("No change in website data")

    # status.json सिर्फ़ तब लिखें जब कुछ बदला हो या गड़बड़ी की हालत बदली हो (बेकार commit से बचने के लिए)
    new_status = {"lastChange": now if (changed_live or c1 or c2) else status.get("lastChange"),
                  "courses": len(live_courses), "videos": len(live_blogs), "errors": errors}
    if (changed_live or c1 or c2) or status.get("errors") != errors:
        save_json(STATUS_FILE, new_status)
    if len(errors) == 2:
        sys.exit(1)


if __name__ == "__main__":
    main()
