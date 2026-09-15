import copy
import json
import threading
import urllib.error
import urllib.request

import pytest

from arsenal.conversation import ConversationStore
from arsenal.performance import PerformanceStore
from arsenal.replay import Server


@pytest.fixture
def setup(tmp_path):
    performance=PerformanceStore(tmp_path/"performance")
    session=performance.open()
    performance.append(session,[{"kind":"on","t_ms":0,"note":60,"vel":80},
        {"kind":"off","t_ms":500,"note":60},{"kind":"sound_end","t_ms":500,"note":60,"by":"release"},
        {"kind":"on","t_ms":1000,"note":64,"vel":95},
        {"kind":"off","t_ms":2000,"note":64},{"kind":"sound_end","t_ms":2000,"note":64,"by":"release"}])
    store=ConversationStore(tmp_path/"conversation",performance)
    doc={"cards":[{"id":"test-question","title":"A little turn","group":"Test","observation":"A note moves.",
        "question":"Where would you go next?","prompt":"Play an answer.",
        "clips":[{"session":session,"at":"0:00","seconds":2,"label":"The source"}]}]}
    store.publish(doc)
    return store,performance,session,doc


def test_publish_checks_all_clips_before_replacing_existing(setup):
    store,_,_,doc=setup
    before=(store.root/"conversation.json").read_bytes()
    bad=copy.deepcopy(doc);bad["cards"][0]["clips"][0]["at"]="9:00"
    with pytest.raises(ValueError):store.publish(bad)
    assert (store.root/"conversation.json").read_bytes()==before


def test_answer_is_attached_to_question_and_cut_without_mutating_log(setup):
    store,perf,session,_=setup
    before={p:p.read_bytes() for p in perf.root.rglob("*") if p.is_file()}
    body={"id":"a"*32,"card_id":"test-question","session":session,"start_ms":900,"end_ms":1500,"note":"This felt settled."}
    result=store.save_response(body)
    assert result["question"]=="Where would you go next?"
    assert result["note_count"]==1
    step=result["replay"]["cue"]["steps"][0]
    assert (step["notes"],step["at_ms"],step["hold_ms"],step["velocity"])==([64],100,500,95)
    assert store.save_response(body)==result
    assert len(store.responses())==1
    assert {p:p.read_bytes() for p in before}==before
    with pytest.raises(ValueError,match="different answer"):store.save_response({**body,"end_ms":1600})


@pytest.mark.parametrize("change",[{"end_ms":float("nan")},{"end_ms":62000},{"start_ms":-1},
    {"card_id":"missing"},{"id":"../escape"},{"start_ms":600,"end_ms":900}])
def test_refuses_invalid_or_empty_answers(setup,change):
    store,_,session,_=setup
    body={"id":"b"*32,"card_id":"test-question","session":session,"start_ms":900,"end_ms":1500}
    with pytest.raises(ValueError):store.save_response({**body,**change})
    assert not store.responses()


def test_http_saves_only_explicit_same_origin_answers(setup):
    store,perf,session,_=setup
    server=Server(0,perf.root,store.root)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_address[1]}"
    body={"id":"c"*32,"card_id":"test-question","session":session,"start_ms":900,"end_ms":1500}
    try:
        for origin,code in [("https://example.com",403),(base,200)]:
            req=urllib.request.Request(base+"/api/conversation/responses",data=json.dumps(body).encode(),
                headers={"Content-Type":"application/json","Origin":origin})
            if code==403:
                with pytest.raises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
                assert e.value.code==403
            else:
                with urllib.request.urlopen(req) as response:assert json.load(response)["note_count"]==1
        with urllib.request.urlopen(base+"/api/conversation/replay/"+body["id"]) as response:
            assert json.load(response)["cue"]["source"]=="replay"
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)
