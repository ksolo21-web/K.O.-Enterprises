"""Conservative manufacturer-specific age research. Never guess an installation date."""
from __future__ import annotations
from datetime import date
import re
BW_YEAR = 'ABCDEFGHJKLMNPSTWXYZ'  # years 1984..2003, every 20 years
BW_MONTH = 'ABCDEFGHJKLM'  # Jan-Dec; I omitted
SOURCE = 'https://forthepro.bradfordwhite.com/determining-the-age-of-a-water-heater/'
OFFICIAL = 'https://www.bradfordwhite.com/my-water-heater/'

MANUFACTURER_SOURCES = {
    'bradford white': SOURCE,
    'rheem': 'https://www.rheem.com/how-to-locate-and-read-your-rheem-water-heating-serial-numbers/',
    'carrier': 'https://www.carrier.com/us/en/residential/homeowner-resources/warranty-lookup/',
    'goodman': 'https://www.goodmanmfg.com/resources/hvac-learning-center/warranty',
    'a.o. smith': 'https://www.aosmithatlowes.com/owner-center/need-more-help/',
    'ao smith': 'https://www.aosmithatlowes.com/owner-center/need-more-help/',
}


def research_equipment(brand: str, serial: str, inspection_date: str) -> dict:
    """Trusted manufacturer-source triage, NOT a real-time warranty-portal lookup.

    Parsers apply only to narrow source-documented formats, without model OCR.
    """
    normalized = re.sub(r'\s+', ' ', str(brand or '').strip().lower().replace('-', ' '))
    s = re.sub(r'\s+', '', str(serial or '').upper())
    result = {'brand':brand, 'serial':serial, 'manufacturer_date':None,
              'candidates':[], 'verification':'not_verified',
              'source':MANUFACTURER_SOURCES.get(normalized),
              'note':'Manufacturer-specific warranty or rating-plate lookup is required.'}
    as_of = date.fromisoformat(inspection_date)
    if normalized == 'rheem':
        # Rheem's published water-heater example: MM YY plant-letter #####.
        # Do not apply to all Rheem product lines or unknown historic formats.
        match = re.fullmatch(r'(0[1-9]|1[0-2])(\d{2})[A-Z]\d{5}', s)
        if match:
            month, year = int(match[1]), 2000+int(match[2])
            if (year,month) <= (as_of.year,as_of.month):
                result.update(manufacturer_date=f'{year:04d}-{month:02d}',
                              candidates=[f'{year:04d}-{month:02d}'],
                              verification='manufacturer_code_only',
                              note='Decoded only for the manufacturer-published MMYY plant-code water-heater format; validate model/rating plate and official warranty record.')
                return result
        result['note']='Rheem format not unambiguously matched or date after inspection; verify product line and manufacturer portal.'
        return result
    if normalized != 'bradford white':
        return result
    if not re.fullmatch(r'[A-Z][A-Z]\d{7,8}', s):
        result['note']='Serial format is not recognized; verify against the rating plate and manufacturer.'
        return result
    if s[:2]=='OA':  # manufacturer documented 1997 exception
        result.update(candidates=['1997-01'], manufacturer_date='1997-01',verification='manufacturer_code_only',note='Documented 1997 OA code exception; confirm with official warranty lookup.')
        return result
    if s[0] not in BW_YEAR or s[1] not in BW_MONTH:
        result['note']='Code characters do not match published manufacturer date code.'
        return result
    base_year=1984 + BW_YEAR.index(s[0])
    month=BW_MONTH.index(s[1])+1
    years=[]
    for y in range(base_year,as_of.year+1,20):
        if (y,month)>(as_of.year,as_of.month):
            continue
        # Bradford White: 7 digits before Dec 2007; 8 digits from Dec 2007.
        if len(s)==9 and (y,month)>=(2007,12): continue
        if len(s)==10 and (y,month)<(2007,12): continue
        years.append(f'{y:04d}-{month:02d}')
    result['candidates']=years
    if len(years)==1:
        result['manufacturer_date']=years[0]
        result['verification']='manufacturer_code_only'
        result['note']='Decoded from official year/month code. Not installation date; verify via manufacturer lookup/rating plate.'
    elif years:
        result['verification']='ambiguous_cycle'
        result['note']='Year letters repeat every 20 years. Candidate dates require corroboration.'
    else:
        result['note']='Date code conflicts with serial length or inspection date; verify manually.'
    return result
