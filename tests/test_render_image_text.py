from app.design.render_image import _sentence_from_text


def test_image_sentence_uses_one_complete_sentence_without_cut_words() -> None:
    text = "AI-инфраструктура становится главным дефицитом рынка США. Второе предложение."

    assert _sentence_from_text(text) == "AI-инфраструктура становится главным дефицитом рынка США."


def test_image_sentence_rejects_forbidden_service_phrases() -> None:
    assert _sentence_from_text("Альтернативный вариант обложки") == (
        "Главная тема рынка США получает новый импульс."
    )
    assert _sentence_from_text("На радаре") == "Главная тема рынка США получает новый импульс."


def test_image_sentence_truncates_by_words() -> None:
    sentence = " ".join(["рынок"] * 40)

    result = _sentence_from_text(sentence)

    assert len(result) <= 93
    assert result.endswith(".")
    assert all(word == "рынок" for word in result.removesuffix(".").split())
