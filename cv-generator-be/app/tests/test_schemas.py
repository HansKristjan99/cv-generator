from app.schemas import CurriculumVitae, CVWriterResponse, OtherMessage


def _minimal_cv() -> CurriculumVitae:
    return CurriculumVitae(
        name="Test Person",
        location="Zürich, Switzerland",
        email="test@example.com",
        phone=None,
        links=[],
        summary="Engineer.",
        experience=[],
        education=[],
        skills=[],
        projects=[],
        awards=[],
        job_requirements=[],
        target_pages=1,
    )


def test_schema_round_trip() -> None:
    cv = _minimal_cv()
    assert CurriculumVitae.model_validate_json(cv.model_dump_json()) == cv


def test_json_schema_is_strict_compatible() -> None:
    schema = CurriculumVitae.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"].keys())


def test_cv_writer_response_round_trip() -> None:
    response = CVWriterResponse(content=_minimal_cv())
    assert CVWriterResponse.model_validate_json(response.model_dump_json()) == response


def test_cv_writer_response_schema_is_strict_compatible() -> None:
    schema = CVWriterResponse.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"].keys())


def test_other_message_variant() -> None:
    response = CVWriterResponse(content=OtherMessage(text="Glad to help!"))
    parsed = CVWriterResponse.model_validate_json(response.model_dump_json())
    assert isinstance(parsed.content, OtherMessage)
    assert parsed.content.text == "Glad to help!"
