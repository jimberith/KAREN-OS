from karenos.web.features.intents import classify_intent


def test_routes_web_search():
    assert classify_intent("Search the web for current AI news").kind == "web_search"


def test_routes_image_generation():
    assert classify_intent("Generate an image of a futuristic assistant").kind == "image_generation"


def test_routes_memory_commands():
    assert classify_intent("Remember that my project is called KAREN").kind == "remember"
    assert classify_intent("What do you remember about my project?").kind == "recall"


def test_routes_only_approved_device_actions():
    action = classify_intent("Open YouTube")
    assert action.kind == "automation"
    assert action.action == {"name": "open_website", "target": "youtube"}

    volume = classify_intent("Mute the volume")
    assert volume.kind == "automation"
    assert volume.action == {"name": "volume", "target": "mute"}


def test_ambiguous_text_remains_chat():
    assert classify_intent("Tell me about computer vision").kind == "chat"
