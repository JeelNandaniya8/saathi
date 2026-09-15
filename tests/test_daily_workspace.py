"""Review intervals and local clocks without external services."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import pytest
import daily_workspace as daily


def test_quiet_hours_are_local_and_end_exclusive():
    p={**daily.DEFAULTS,'timezone':'Asia/Kolkata','quiet_enabled':True}
    assert not daily.quiet_now(p,datetime(2026,9,15,16,29,tzinfo=timezone.utc))
    assert daily.quiet_now(p,datetime(2026,9,15,16,30,tzinfo=timezone.utc))
    assert daily.quiet_now(p,datetime(2026,9,16,2,29,tzinfo=timezone.utc))
    assert not daily.quiet_now(p,datetime(2026,9,16,2,30,tzinfo=timezone.utc))
    p.update(quiet_start='12:00',quiet_end='14:00')
    assert daily.quiet_now(p,datetime(2026,9,15,7,tzinfo=timezone.utc))
    assert not daily.quiet_now(p,datetime(2026,9,15,9,tzinfo=timezone.utc))


@pytest.mark.parametrize('data',[
    [],{'goal':[]},{'quiet_enabled':'yes'},{'timezone':'Not/AZone'},
    {'quiet_start':'25:00'},{'digest_time':None},{'celebrations':1},
    {'language':['gu']},{'unexpected':'field'},
    {'quiet_enabled':True,'quiet_start':'08:00','quiet_end':'08:00'},
    {'quiet_enabled':True,'notification_mode':'digest','digest_time':'23:00'}
])
def test_invalid_preferences_are_rejected(data):
    with pytest.raises(ValueError):daily.validated_preferences(data,daily.DEFAULTS)


def test_review_schedule_retains_hard_progress_and_resets_again():
    now=datetime(2026,9,15,tzinfo=timezone.utc);reps=0
    for days in (1,3,7,14,30,30):
        due,reps=daily.review_schedule('good',reps,now)
        assert due==now+timedelta(days=days)
    assert daily.review_schedule('hard',reps,now)==(now+timedelta(days=1),reps)
    assert daily.review_schedule('again',reps,now)==(now+timedelta(minutes=10),0)
    with pytest.raises(ValueError):daily.review_schedule('invented',0,now)


def test_flashcard_parser_preserves_languages_and_ignores_other_text():
    text='Outside text\n[FLASHCARDS]\nFront: પ્રશ્ન?\nBack: જવાબ\n---\nFront: सवाल?\nBack: उत्तर\n[/FLASHCARDS]'
    assert daily.flashcards(text)==[('પ્રશ્ન?','જવાબ'),('सवाल?','उत्तर')]
    assert daily.flashcards('Front: Hello\nBack: World')==[]


def test_care_move_preserves_wall_clock_across_dst():
    now=datetime(2026,3,7,12,tzinfo=timezone.utc);due=datetime(2026,3,7,15,tzinfo=timezone.utc)
    moved=daily.moved_due(due,now,ZoneInfo('America/New_York'))
    assert moved==datetime(2026,3,8,14,tzinfo=timezone.utc)
    assert moved.astimezone(ZoneInfo('America/New_York')).hour==10
