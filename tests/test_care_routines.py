from datetime import datetime,timedelta,timezone
import pytest
import care_routines as care


def test_wall_clock_survives_spring_and_fall_dst():
    anchor=datetime(2026,3,7,13,tzinfo=timezone.utc) # 08:00 New York
    assert care.next_slot(anchor,'daily','America/New_York',anchor)==datetime(2026,3,8,12,tzinfo=timezone.utc)
    anchor=datetime(2026,10,31,12,tzinfo=timezone.utc)
    assert care.next_slot(anchor,'daily','America/New_York',anchor)==datetime(2026,11,1,13,tzinfo=timezone.utc)


def test_gap_overlap_and_weekly_are_deterministic():
    anchor=datetime(2026,3,7,7,30,tzinfo=timezone.utc)
    assert care.next_slot(anchor,'daily','America/New_York',anchor)==datetime(2026,3,8,7,30,tzinfo=timezone.utc)
    anchor=datetime(2026,10,31,5,30,tzinfo=timezone.utc)
    assert care.next_slot(anchor,'daily','America/New_York',anchor)==datetime(2026,11,1,5,30,tzinfo=timezone.utc)
    assert care.next_slot(anchor,'weekly','America/New_York',anchor)==datetime(2026,11,7,6,30,tzinfo=timezone.utc)
    assert care.next_slot(anchor,'once','UTC',anchor) is None


def data(**kwargs):
    return {'title':'User entered schedule','instructions':'Exact clinician-provided text', 'timezone':'Asia/Kolkata',
            'starts_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'recurrence':'daily','confirmed':True,**kwargs}

@pytest.mark.parametrize('change',[{'confirmed':False},{'instructions':''},{'title':None},{'timezone':'Invalid/Zone'},{'starts_at':'bad'},{'starts_at':'2026-10-08T09:00'},{'recurrence':[]},{'instructions':'a'*501}])
def test_requires_confirmed_exact_instruction_and_aware_time(change):
    with pytest.raises(ValueError):care.validate_schedule(data(**change))


def test_confirmation_does_not_infer_or_rewrite_instructions():
    title,note,repeat,schedule=care.validate_schedule(data())
    assert note=='Exact clinician-provided text' and repeat=='daily'
    assert schedule['timezone']=='Asia/Kolkata'


def test_sync_batches_do_not_starve_schedules_after_first_hundred(monkeypatch):
    monkeypatch.setenv('CARE_ROUTINES_ENABLED','true')
    visited=[]
    class Cursor:
        def execute(self,query,params):
            self.after=params[1]
        def fetchall(self):
            return [{'id':i} for i in range(self.after+1,min(self.after+100,205)+1)]
        def close(self):pass
    class Connection:
        def cursor(self):return Cursor()
        def commit(self):pass
        def rollback(self):pass
        def close(self):pass
    monkeypatch.setattr(care,'sync_one',lambda cur,row,now:visited.append(row['id']))
    care.sync_due({'get_db':Connection})
    assert visited==list(range(1,206))
