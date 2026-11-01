"""Minimal OS images still resolve stored Indian timezone aliases."""
import os
import subprocess
import sys


def test_packaged_timezone_works_without_operating_system_database():
    source = "from zoneinfo import ZoneInfo; from datetime import datetime; assert datetime(2026,10,31,tzinfo=ZoneInfo('Asia/Calcutta')).utcoffset().total_seconds()==19800; assert ZoneInfo('Asia/Kolkata'); assert ZoneInfo('America/New_York')"
    subprocess.run([sys.executable, '-c', source], env={**os.environ, 'PYTHONTZPATH':''}, check=True)
