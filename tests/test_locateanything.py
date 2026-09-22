from embodied_runtime.adapters.locateanything import parse_locateanything


def test_locateanything_parser_scales_and_rejects_invalid():
    result = parse_locateanything("<ref>drawer</ref><box><100><200><900><800></box><box><0><0><1001><2></box>", 384, 256)
    assert result["references"] == ["drawer"]
    assert result["boxes_xyxy"] == [[38.4, 51.2, 345.6, 204.8]]
