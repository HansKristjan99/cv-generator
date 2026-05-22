from app.schemas import CoverLetter, CurriculumVitae, Education, JobExperience
from app.services.latex import cover_letter_to_latex, cv_to_latex
from app.services.latex_escape import escape_cover_letter_for_latex


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
            ),
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
        job_requirements=[],
    )
    latex_str = cv_to_latex(cv)
    assert "\\begin{document}" in latex_str
    assert "\\end{document}" in latex_str


def test_cover_letter_to_latex() -> None:
    cl = CoverLetter(
        name="Test Person",
        title="Software Engineer",
        email="test@example.com",
        phone=None,
        location="Tallinn, Estonia",
        linkedin="https://linkedin.com/in/testperson",
        recipient="Hiring Team",
        company="Acme & Sons",
        greeting="Dear",
        body=(
            "Opening paragraph with a hook and 50% growth.\n\n"
            "Second paragraph: shipped X, measured by Y.\n\n"
            "Third paragraph about collaboration & communication.\n\n"
            "Closing paragraph with motivation."
        ),
        closer="Sincerely",
    )
    latex_str = cover_letter_to_latex(escape_cover_letter_for_latex(cl))
    assert "\\begin{document}" in latex_str
    assert "\\end{document}" in latex_str
    # JD/company free text must be LaTeX-escaped, not raw.
    assert "Acme \\& Sons" in latex_str
    assert "50\\%" in latex_str
    assert "Dear Hiring Team," in latex_str
    # email goes into an \href display position escaped, mailto raw.
    assert "mailto:test@example.com" in latex_str
