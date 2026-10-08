"""Prevent silent language gaps in the registered legacy UI catalog."""
import json
from pathlib import Path


def catalog(language):
    source=Path('locale-'+language+'.js').read_text()
    return json.loads(source[source.index('{'):source.rindex('}')+1])


def test_gujarati_and_hindi_have_matching_complete_catalogs():
    gu,hi=catalog('gu'),catalog('hi')
    assert len(gu)>=699 and gu.keys()==hi.keys()
    for data in (gu,hi):
        assert all(isinstance(v,str) and v.strip() for v in data.values())
        assert all('<script' not in v.casefold() for v in data.values())
    for key in ('Please log in first.','Your workspace is ready.','Delete account permanently','The request took too long. Please retry.'):
        assert gu[key]!=key and hi[key]!=key
