from app.src.schemas.output_types.responses.cv import CurriculumVitae
from app.src.schemas.output_types.responses import CVWriterResponse


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
    )


def test_schema_round_trip() -> None:
    cv = _minimal_cv()
    assert CurriculumVitae.model_validate_json(cv.model_dump_json()) == cv


def test_json_schema_is_strict_compatible() -> None:
    schema = CurriculumVitae.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"].keys())


def test_cv_writer_response_round_trip() -> None:
    response = CVWriterResponse(curriculum_vitae=_minimal_cv(), job_requirements=[])
    assert CVWriterResponse.model_validate_json(response.model_dump_json()) == response


def test_cv_writer_response_schema_is_strict_compatible() -> None:
    schema = CVWriterResponse.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"].keys())
