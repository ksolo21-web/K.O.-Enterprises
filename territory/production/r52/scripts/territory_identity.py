#!/usr/bin/env python3
import re

ALLOWED_CLASSES={"","A","T","TA"}
SUFFIX_RE=re.compile(r"^[a-z]*$")
MASTERISH_RE=re.compile(r"^(?:R|A|T|TA)-?\d+(?:-[A-Za-z]+)?$")

def normalize_base(v):
    if isinstance(v,bool): raise ValueError('base_number must be integer-like, not bool')
    try: n=int(str(v).strip())
    except Exception as e: raise ValueError('base_number must be a positive integer') from e
    if n<=0: raise ValueError('base_number must be positive')
    return n

def normalize_class(v):
    c=str(v or '').strip().upper()
    if c=='R': raise ValueError('R is source/master classification only; residential/default card_class must be empty')
    if c not in ALLOWED_CLASSES: raise ValueError('card_class must be one of empty, A, T, TA')
    return c

def normalize_suffix(v):
    s=str(v or '').strip()
    if s and not SUFFIX_RE.fullmatch(s):
        raise ValueError('suffix must be lowercase letters only; source directional markers require explicit identity resolution')
    return s

def derive(base_number, card_class='', suffix=''):
    n=normalize_base(base_number); c=normalize_class(card_class); s=normalize_suffix(suffix)
    display=f'{c}{n}{s}'
    filename=f'Territory - {n:03d}{c}{s}.pdf'
    return {'base_number':n,'card_class':c,'suffix':s,'display_id':display,'canonical_filename':filename}

def looks_like_master_alias(value):
    v=str(value or '').strip()
    return bool(MASTERISH_RE.fullmatch(v)) and '-' in v