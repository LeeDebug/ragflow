

from nltk.stem import PorterStemmer
stemmer = PorterStemmer()

import re
from nltk import word_tokenize
from . import huqie
from rag.utils import num_tokens_from_string
import random

BULLET_PATTERN = [[
    r"第[零一二三四五六七八九十百0-9]+(分?编|部分)",
    r"第[零一二三四五六七八九十百0-9]+章",
    r"第[零一二三四五六七八九十百0-9]+节",
    r"第[零一二三四五六七八九十百0-9]+条",
    r"[\(（][零一二三四五六七八九十百]+[\)）]",
], [
    r"第[0-9]+章",
    r"第[0-9]+节",
    r"[0-9]{,3}[\. 、]",
    r"[0-9]{,2}\.[0-9]{,2}",
    r"[0-9]{,2}\.[0-9]{,2}\.[0-9]{,2}",
    r"[0-9]{,2}\.[0-9]{,2}\.[0-9]{,2}\.[0-9]{,2}",
], [
    r"第[零一二三四五六七八九十百0-9]+章",
    r"第[零一二三四五六七八九十百0-9]+节",
    r"[零一二三四五六七八九十百]+[ 、]",
    r"[\(（][零一二三四五六七八九十百]+[\)）]",
    r"[\(（][0-9]{,2}[\)）]",
], [
    r"PART (ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)",
    r"Chapter (I+V?|VI*|XI|IX|X)",
    r"Section [0-9]+",
    r"Article [0-9]+"
]
]


def random_choices(arr, k):
    k = min(len(arr), k)
    return random.choices(arr, k=k)


def bullets_category(sections):
    global BULLET_PATTERN
    hits = [0] * len(BULLET_PATTERN)
    for i, pro in enumerate(BULLET_PATTERN):
        for sec in sections:
            for p in pro:
                if re.match(p, sec):
                    hits[i] += 1
                    break
    maxium = 0
    res = -1
    for i, h in enumerate(hits):
        if h <= maxium: continue
        res = i
        maxium = h
    return res


def is_english(texts):
    eng = 0
    for t in texts:
        if re.match(r"[a-zA-Z]{2,}", t.strip()):
            eng += 1
    if eng / len(texts) > 0.8:
        return True
    return False


def tokenize(d, t, eng):
    d["content_with_weight"] = t
    if eng:
        t = re.sub(r"([a-z])-([a-z])", r"\1\2", t)
        d["content_ltks"] = " ".join([stemmer.stem(w) for w in word_tokenize(t)])
    else:
        d["content_ltks"] = huqie.qie(t)
        d["content_sm_ltks"] = huqie.qieqie(d["content_ltks"])


def remove_contents_table(sections, eng=False):
    i = 0
    while i < len(sections):
        def get(i):
            nonlocal sections
            return (sections[i] if type(sections[i]) == type("") else sections[i][0]).strip()

        if not re.match(r"(contents|目录|目次|table of contents|致谢|acknowledge)$",
                        re.sub(r"( | |\u3000)+", "", get(i).split("@@")[0], re.IGNORECASE)):
            i += 1
            continue
        sections.pop(i)
        if i >= len(sections): break
        prefix = get(i)[:3] if not eng else " ".join(get(i).split(" ")[:2])
        while not prefix:
            sections.pop(i)
            if i >= len(sections): break
            prefix = get(i)[:3] if not eng else " ".join(get(i).split(" ")[:2])
        sections.pop(i)
        if i >= len(sections) or not prefix: break
        for j in range(i, min(i + 128, len(sections))):
            if not re.match(prefix, get(j)):
                continue
            for _ in range(i, j): sections.pop(i)
            break


def make_colon_as_title(sections):
    if not sections: return []
    if type(sections[0]) == type(""): return sections
    i = 0
    while i < len(sections):
        txt, layout = sections[i]
        i += 1
        txt = txt.split("@")[0].strip()
        if not txt:
            continue
        if txt[-1] not in ":：":
            continue
        txt = txt[::-1]
        arr = re.split(r"([。？！!?;；]| .)", txt)
        if len(arr) < 2 or len(arr[1]) < 32:
            continue
        sections.insert(i - 1, (arr[0][::-1], "title"))
        i += 1


def hierarchical_merge(bull, sections, depth):
    if not sections or bull < 0: return []
    if type(sections[0]) == type(""): sections = [(s, "") for s in sections]
    sections = [(t,o) for t, o in sections if t and len(t.split("@")[0].strip()) > 1 and not re.match(r"[0-9]+$", t.split("@")[0].strip())]
    bullets_size = len(BULLET_PATTERN[bull])
    levels = [[] for _ in range(bullets_size + 2)]

    def not_title(txt):
        if re.match(r"第[零一二三四五六七八九十百0-9]+条", txt): return False
        if len(txt) >= 128: return True
        return re.search(r"[,;，。；！!]", txt)

    for i, (txt, layout) in enumerate(sections):
        for j, p in enumerate(BULLET_PATTERN[bull]):
            if re.match(p, txt.strip()) and not not_title(txt):
                levels[j].append(i)
                break
        else:
            if re.search(r"(title|head)", layout):
                levels[bullets_size].append(i)
            else:
                levels[bullets_size + 1].append(i)
    sections = [t for t, _ in sections]
    for s in sections: print("--", s)

    def binary_search(arr, target):
        if not arr: return -1
        if target > arr[-1]: return len(arr) - 1
        if target < arr[0]: return -1
        s, e = 0, len(arr)
        while e - s > 1:
            i = (e + s) // 2
            if target > arr[i]:
                s = i
                continue
            elif target < arr[i]:
                e = i
                continue
            else:
                assert False
        return s

    cks = []
    readed = [False] * len(sections)
    levels = levels[::-1]
    for i, arr in enumerate(levels[:depth]):
        for j in arr:
            if readed[j]: continue
            readed[j] = True
            cks.append([j])
            if i + 1 == len(levels) - 1: continue
            for ii in range(i + 1, len(levels)):
                jj = binary_search(levels[ii], j)
                if jj < 0: continue
                if jj > cks[-1][-1]: cks[-1].pop(-1)
                cks[-1].append(levels[ii][jj])
            for ii in cks[-1]: readed[ii] = True
    for i in range(len(cks)):
        cks[i] = [sections[j] for j in cks[i][::-1]]
        print("--------------\n", "\n* ".join(cks[i]))

    return cks


def naive_merge(sections, chunk_token_num=128, delimiter="\n。；！？"):
    if not sections: return []
    if type(sections[0]) == type(""): sections = [(s, "") for s in sections]
    cks = [""]
    tk_nums = [0]
    def add_chunk(t, pos):
        nonlocal cks, tk_nums, delimiter
        tnum = num_tokens_from_string(t)
        if tnum < 8: pos = ""
        if tk_nums[-1] > chunk_token_num:
            cks.append(t + pos)
            tk_nums.append(tnum)
        else:
            cks[-1] += t + pos
            tk_nums[-1] += tnum

    for sec, pos in sections:
        s, e = 0, 1
        while e < len(sec):
            if sec[e] in delimiter:
                add_chunk(sec[s: e+1], pos)
                s = e + 1
                e = s + 1
            else:
                e += 1
        if s < e: add_chunk(sec[s: e], pos)

    return cks
