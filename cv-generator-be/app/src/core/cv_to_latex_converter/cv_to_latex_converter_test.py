from app.src.api.cv_generator.cv_to_latex_converter.cv_to_latex_converter import cv_to_latex
from app.src.schemas.output_types.responses.cv import CurriculumVitae, Education, JobExperience


def test_cv_to_latex() -> None:
    cv = CurriculumVitae(
        name="Test Person",
        location="Zürich, Switzerland",
        email="test@example.com",
        phone=None,
        links=[],
        summary="Engineer.",
        experience=[
            JobExperience(
                company="Test Company",
                location="Zürich, Switzerland",
                position="Software Engineer",
                start_date="Jan 2020",
                end_date="Present",
                bullets=[
                    "Developed a web application using React and Node.js.",
                    "Implemented RESTful APIs for data retrieval.",
                ],
            ),
            JobExperience(
                company="Test Company 2",
                location="Zürich, Switzerland",
                position="Senior Software Engineer",
                start_date="Jan 2020",
                end_date="Present",
                bullets=[
                    "Developed a web application using React and Node.js.",
                    "Implemented RESTful APIs for data retrieval.",
                ],
            )
        ],
        education=[
            Education(
                institution="Test University",
                location="Zürich, Switzerland",
                degree="B.Sc. in Computer Science",
                start_date="Sep 2015",
                end_date="Jun 2019",
                gpa="4.0/5.0",
                thesis="A Study on the Impact of AI in Modern Software Development",
                coursework="Data Structures, Algorithms, Machine Learning",
            )
        ],
        skills=[],
        projects=[],
        awards=[],
    )
    latex_str = cv_to_latex(cv)
    assert "\\begin{document}" in latex_str
    assert "\\end{document}" in latex_str
    print(latex_str)
