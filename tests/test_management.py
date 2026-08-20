from datetime import date

from fastapi.testclient import TestClient

from planner.api import app

client = TestClient(app)


def test_subject_topic_exam_profile_crud(tmp_path, monkeypatch):
    from planner import api
    from planner.storage import StudyDB
    api.db = StudyDB(tmp_path / "planner.db")

    subject = client.post('/subjects', json={'id':'cardio','name':'Cardiology','exam_weight':1.2,'category':'clinical'})
    assert subject.status_code == 200

    topic = client.post('/topics', json={'id':'heart-failure','subject_id':'cardio','name':'Heart failure','complexity':0.7,'estimated_hours':2.5,'mastery':0.2,'self_difficulty':4,'volume':0.7,'cognitive_load':0.8})
    assert topic.status_code == 200

    exam = client.post('/exams', json={'id':'cardio-block','date':str(date.today()),'subject_ids':['cardio'],'topic_ids':['heart-failure'],'weight':1.5})
    assert exam.status_code == 200

    profile = client.put('/profile', json={'daily_available_minutes':180,'minimum_subject_minutes_week':45,'review_fraction':0.3,'max_session_minutes':45,'rest_weekdays':[4,6],'energy_pattern':['high','high','medium','low']})
    assert profile.status_code == 200
    assert profile.json()['rest_weekdays'] == [4,6]

    snap = client.get('/snapshot').json()
    assert len(snap['subjects']) == 1
    assert len(snap['topics']) == 1
    assert len(snap['exams']) == 1

    assert client.delete('/exams/cardio-block').status_code == 200
    assert client.delete('/topics/heart-failure').status_code == 200
    assert client.delete('/subjects/cardio').status_code == 200
