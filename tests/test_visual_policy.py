from app.design.generate_ai_image import _image_prompt, _image_size
from app.design.visual_policy import load_visual_policy, select_visual_type


def test_visual_policy_has_channel_native_formats() -> None:
    policy = load_visual_policy()
    names = {item["name"] for item in policy["visual_types"]}

    assert "market_terminal" in names
    assert "company_product_context" in names
    assert "deal_or_flow_structure" in names


def test_image_prompt_uses_editorial_visual_logic_not_flat_cards() -> None:
    prompt = _image_prompt(
        {
            "title": "Банковский сектор получает импульс от ожиданий снижения ставок",
            "tickers": ["JPM", "BAC", "XLF"],
            "sources": [{"summary": "Fresh verified market signal from connected sources"}],
        },
        2,
    )

    assert "evidence-first" in prompt
    assert "flat fintech card" in prompt
    assert "Do not solve the variation by changing only colors" in prompt
    assert "выдуманные логотипы компаний" in prompt


def test_image_variants_cycle_through_different_sizes_and_visual_types() -> None:
    first = select_visual_type(1)
    second = select_visual_type(2)
    fifth = select_visual_type(5)

    assert first["name"] != second["name"]
    assert _image_size(1) == "1536x1024"
    assert _image_size(5) == "1024x1536"
    assert fifth["name"] == "deal_or_flow_structure"
