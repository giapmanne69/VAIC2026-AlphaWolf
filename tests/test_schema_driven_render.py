from src.agent import AgenticReportAgent


def build_agent():
    agent = AgenticReportAgent.__new__(AgenticReportAgent)
    agent.agent_state = {}
    return agent


def test_schema_driven_render_context_uses_template_text_fields():
    agent = build_agent()
    schema = {
        "variables": [
            {"name": "tong_thu", "type": "number"},
            {"name": "nhan_xet_kinh_te", "type": "string"},
            {"name": "nhan_xet_van_hoa", "type": "string"},
            {"name": "ky_bao_cao", "type": "string"},
        ]
    }

    render_context = agent._build_render_context_from_schema(
        schema,
        {"tong_thu": 1000},
        {
            "nhan_xet_kinh_te": "Tình hình kinh tế tăng trưởng ổn định.",
            "nhan_xet_van_hoa": "Công tác văn hóa xã hội được triển khai tốt.",
        },
    )

    assert render_context["tong_thu"] == 1000
    assert render_context["nhan_xet_kinh_te"] == "Tình hình kinh tế tăng trưởng ổn định."
    assert render_context["nhan_xet_van_hoa"] == "Công tác văn hóa xã hội được triển khai tốt."
    assert "nhan_xet_ai_kinh_te" not in render_context
