"""Utility functions for ra_mapper"""

import time
import datetime
import unicodedata
import Levenshtein


def now_millis():
    return time.time_ns() // 1_000_000


def remove_specials(text):
    return "".join([char for char in text if char.isalnum() or char == ' '])


def normalize_name(name):

    name = "".join([c for c in unicodedata.normalize('NFKD', name) if not unicodedata.combining(c)])
    name = name.lower()
    name = remove_specials(name)
    name = " ".join(name.split())

    return name.strip()


def str_distance(str1, str2):
    return Levenshtein.distance(str1, str2)

def parse_ra_name(name) -> tuple[str, str, list[str]]:


    SUBSET_TEXT = "Subset - "

    # State Machine
    S_TAGS = 0,
    S_TAG_NAME = 1
    S_TITLE = 2
    S_TITLE_SPACE = 3
    S_SUBSET = 4
    S_SUBSET_NAME = 5


    state = S_TAGS

    begin = 0
    length = 0

    out_title = ""
    out_subset = ""
    out_tags = []

    c = '\0'
    for i in range(len(name)):

        c = name[i]

        if state == S_TAGS:
            if c == '~':
                state = S_TAG_NAME
                begin = i + 1
                length = 0
            elif c != ' ':
                state = S_TITLE
                begin = i
                length = 1

        elif state == S_TAG_NAME:
            if c == '~':
                state = S_TAGS
                tag = name[begin:begin+length]
                out_tags.append(tag)
            else:
                length += 1

        elif state == S_TITLE:
            if c == ' ':
                state = S_TITLE_SPACE
            else:
                length += 1

        elif state == S_TITLE_SPACE:
            if c == '[':
                state = S_SUBSET
                out_title = name[begin:begin+length]
                length = 0
            else:
                state = S_TITLE
                length += 2

        elif state == S_SUBSET:
            if length == len(SUBSET_TEXT):
                state = S_SUBSET_NAME
                begin = i
                length = 0
            elif c != SUBSET_TEXT[length]:
                state = S_TITLE
                length += len(out_title) + 2
            length += 1

        elif state == S_SUBSET_NAME:
            length += 1

    if state == S_SUBSET_NAME:
        if c == ']': 
            out_subset = name[begin:begin+length-1]
        else:
            state = S_TITLE
            length += len(out_title)

    if state == S_TITLE:
        out_title = name[begin : begin + length]

    return (out_title, out_subset, out_tags)


def parse_ra_date(date_str):

    if date_str is None or len(date_str) != 19:
        return None

    year = int(date_str[0:4])
    month = int(date_str[5:7])
    day = int(date_str[8:10])
    hour = int(date_str[11:13])
    minute = int(date_str[14:16])
    second = int(date_str[17:19])

    return datetime.datetime(year, month, day, hour, minute, second).timestamp() * 1000
