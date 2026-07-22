import os
def test_agent_id_env():
    print("AKASHIC_AGENT_ID:", os.environ.get("AKASHIC_AGENT_ID", "NOT SET"))
    assert True
