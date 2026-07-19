from src.agent import AgenticReportAgent


def build_agent():
    agent = AgenticReportAgent.__new__(AgenticReportAgent)
    return agent


def test_scan_template_placeholders_detects_placeholders_and_uses_string_type_default():
    agent = build_agent()
    schema = agent._scan_template_placeholders(
        "Báo cáo tuần:\n- Tổng số hộ: {{ tong_so_ho }}\n- Nhận xét: {{ nhan_xet_tinh_hinh }}"
    )

    assert isinstance(schema, dict)
    assert "variables" in schema
    assert any(var["name"] == "tong_so_ho" for var in schema["variables"])
    assert any(var["name"] == "nhan_xet_tinh_hinh" for var in schema["variables"])
    assert all(var["type"] == "string" for var in schema["variables"])


def test_validate_schema_accepts_strict_number_and_string_types():
    agent = build_agent()
    valid_schema = {
        "variables": [
            {"name": "tong_thu", "type": "number"},
            {"name": "nhan_xet", "type": "string"},
        ]
    }
    invalid_schema = {
        "variables": [
            {"name": "tong_thu", "type": "number/string"},
            {"name": "nhan_xet", "type": "text"},
        ]
    }

    assert agent._validate_schema(valid_schema)
    assert not agent._validate_schema(invalid_schema)
