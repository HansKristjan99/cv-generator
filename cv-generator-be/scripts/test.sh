#!/usr/bin/env bash
# Quick e2e smoke test against a locally running server:
#   uv run uvicorn app.main:app --reload  (in another terminal)
#   ./scripts/test.sh
#
# Endpoint: POST http://localhost:8000/cv/generate/
# Form fields (all optional, but at least one required):
#   text             - raw CV text
#   job_description  - job description text
#   file             - uploaded CV file (PDF, etc.)
# Response JSON: { "latex": "<latex string>" }

set -euo pipefail

URL="${URL:-http://localhost:8000/cv/generate/}"
TEXT="\documentclass[10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage[left=1.2cm,top=1.2cm,right=1.2cm,bottom=1.0cm]{geometry}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{parskip}
\usepackage{xcolor}
\setlist[itemize]{noitemsep, topsep=2pt, leftmargin=14pt, parsep=1.5pt}
\pagestyle{empty}
\setlength{\parskip}{0pt}
\newcommand{\cvsection}[1]{\vspace{8pt}{\large \textbf{#1}}\\[-5pt]{\color{black!35}\hrule height 0.4pt}\vspace{5pt}}
\newcommand{\cventry}[4]{\textbf{#1} \hfill #2\\\textit{#3} \hfill #4}
\begin{document}
\small
\begin{center}
    {\LARGE \textbf{Hans Kristjan Veri}}\\[5pt]
    Zürich, Switzerland — EU Citizen (B Permit) \textbullet\ \href{mailto:hans.kristjan.veri@gmail.com}{hans.kristjan.veri@gmail.com} \textbullet\ +41 78 346 33 03
\end{center}
\vspace{4pt}

Frontend-focused engineer with a specialized background in applied cryptography and security. Proven track record of shipping performant React/TypeScript applications for complex enterprise environments. Experienced in building privacy-first software and comfortable owning features from initial UI/UX scoping to backend API design and production monitoring. Dual degrees in CS and Mathematics (cum laude).

\cvsection{Experience}
\cventry{Intonate GmbH}{Zürich, Switzerland}{Software Engineer (Full-Stack)}{Oct 2025 -- Present}
\begin{itemize}
    \item Own end-to-end delivery of features for a B2B SaaS platform serving 2,000+ daily sessions, contributing across client applications and TypeScript/Python backend services.
    \item Built and maintained secure REST and GraphQL APIs using TypeScript and Python (AWS Lambda, AppSync), including authentication, access control, and integration with downstream services.
    \item Rebuilt the onboarding experience into a guided single-page flow, increasing user completion from 50\% to 90\%.
    \item Implemented group-based access control using OAuth 2.0/OIDC across API Gateway, AppSync, and S3, improving multi-tenant isolation for enterprise customers.
    \item Set up monitoring and alerting for production web clients, improving incident response time and debugging visibility.
\end{itemize}

\vspace{5pt}

\cventry{Twilio}{Tallinn, Estonia}{Software Engineer (Front-End)}{Sep 2024 -- Oct 2025}
\begin{itemize}
    \item Developed core features for Twilio Flex, an enterprise platform used by thousands of customers, focusing on high-performance React components for real-time agent workflows.
    \item Modernized legacy UI by introducing a strictly-typed component library, significantly reducing regressions through comprehensive unit and integration testing.
    \item Collaborated with distributed teams across time zones to ship features that required tight integration between frontend UI and complex backend platform services.
    \item Improved release safety and development speed by contributing to CI/CD pipelines and Kubernetes-based end-to-end testing environments.
\end{itemize}

\vspace{5pt}

\cventry{Cybernetica AS}{Tallinn, Estonia}{Research Intern --- Applied Cryptography}{Jun 2024 -- Aug 2024}
\begin{itemize}
    \item Designed and implemented optimized post-quantum threshold signature schemes, reducing public key sizes by over 50\%.
    \item Translated theoretical cryptographic research into practical, production-ready code implementations.
\end{itemize}

\vspace{5pt}

\cventry{University of Tartu}{Tartu, Estonia}{Teaching Assistant}{Jan 2022 -- Jun 2025}
\begin{itemize}
    \item Taught Algorithms and Data Structures, Discrete Mathematics, and Theoretical Computer Science to hundreds of students over 3+ years.
    \item Built automated grading systems in Java, reducing evaluation time from 4 hours to under 30 minutes.
\end{itemize}

\cvsection{Education}
\cventry{University of Tartu}{Tartu, Estonia}{M.Sc. in Computer Science, summa cum laude}{Sep 2023 -- Jun 2025}\\[2pt]
{\footnotesize \textbf{Thesis:} Post-quantum cryptography.. \textbf{Coursework:} Advanced Algorithms, Distributed Systems, System Design, Software Design Patterns..}

\vspace{4pt}

\cventry{University of Tartu}{Tartu, Estonia}{B.Sc. in Mathematics (cum laude) \& B.Sc. in Computer Science}{Sep 2020 -- Aug 2025}

\cvsection{Skills}
\textbf{Languages \& Frameworks:} TypeScript, JavaScript, React, React Native, Flutter, Python, Java, Scala, Node.js, some Rust exposure\\[3pt]
\textbf{Frontend:} Performance optimization, reusable component libraries, testing (Jest/Cypress), accessibility\\[3pt]
\textbf{Backend \& APIs:} REST, GraphQL, serverless (AWS Lambda), microservices\\[3pt]
\textbf{Security \& Privacy:} OAuth 2.0/OIDC, post-quantum signatures, OWASP, client-side security\\[3pt]
\textbf{Infrastructure:} AWS (Lambda, API Gateway, AppSync, S3, CDK), Kubernetes, Docker, Terraform, CI/CD\\[3pt]
\textbf{Languages:} Estonian (native), English (fluent), Russian (basic), German (basic)\\[3pt]
\textbf{Other:} Competitive chess player

\end{document}"
JOB_DESCRIPTION=" About the job

Join Proton and build a better internet where privacy is the default

At Proton, we believe that privacy is a fundamental human right and the cornerstone of democracy. Since our inception in 2014, founded by a team of scientists from CERN, we have dedicated ourselves to providing free and open-source technology to millions worldwide, ensuring access to privacy, security, and freedom online.

Our journey began with Proton Mail, the largest secure email service globally, and has since expanded to include Proton VPN, Proton Calendar, Proton Drive, and Proton Pass. These tools empower individuals and organizations to take control of their personal data, break away from Big Tech’s invasive practices, and defeat censorship. Our work impacts hundreds of millions of lives, from activists on the front lines defending freedom to leaders in governments protecting sensitive information. In some cases, Proton’s services have even been instrumental in saving lives by enabling secure and private communications in high-risk situations.

Proton is a profitable company that does not rely upon VC funding, supporting over 100 million user accounts with a growing team of over 500 people from over 50 different countries, from the world's top companies and universities. We value intelligence, learning potential, and ambition in our hiring process. Adaptability is key as we navigate uncharted territories and redefine how business is conducted online.

Hiring at Proton is highly selective, with less than 1% of candidates hired. We believe smaller teams of exceptional talent will always prevail over larger teams with lower talent density. You will have the opportunity to work with many of the world's top minds in their fields, ranging from former international math and science olympiad winners to chess champions.

We have a global mindset and big ambitions but remain a start-up at heart. We value empowerment and flexibility and keep our structure flat to keep moving fast and avoid unnecessary politics. Tired of blending into the crowd? Join us and do work you can truly be proud of. Check our open-source projects here!

Purpose of the role

MSA is a highly multi-disciplinary group started in 2019 to tackle difficult mail delivery, spam, abuse, and account security problems that impact the Proton ecosystem. We built sophisticated systems from scratch that combine human intelligence and machine learning to make tens of millions of realtime or asynchronous decisions each day. Our custom systems have reduced spam filter misclassifications by over 60%, blocked millions of abusive bulk signups, protected hundreds of thousands of users from account compromise by attackers, and mitigated hundreds of DDoS attacks. In the last few years, we have also been building complicated new products, including launching Wallet, Lumo AI, and Meet. We are the main group at Proton working on AI. In order to move fast with limited resources, we are organized into autonomous teams responsible for the whole system, with expertise across infrastructure, data storage, backend, web and mobile apps, machine learning, security and operational excellence. We are looking for humble, mission-driven, systems-thinking people who want to make a big impact in a startup environment.

What You Will Do

MSA builds and operates many services responsible for different domains. You will:


    work with other engineers and analysts to design, build, and operate these systems
    work on special user-facing features involving frontend and backend software development
    You will have the opportunity to play Product or Project Managers roles and lead the whole planning and development process
    be responsible for the operational excellence of the systems/features and their interaction with other systems
    You may work on MSA's custom systems written in Python or on the main Proton API written in PHP or on Proton Web apps written in React or even on native iOS and Android mobile apps


Job Requirements


    Deep experience with backend development (Python, PHP, or Go)
    Experience with frontend design and development (JavaScript, React, Typescript, or jQuery)
    Experience building complex production systems
    Experience with data processing and storage (MySQL, MongoDB, Redis, Kafka, Elastic, Ceph, ClickHouse)
    Able to work autonomously and lead the whole development process, from design to QA
    Experience with AI tools and AI agents
    Excellent English communications, both written and spoken


Bonus points for:


    experience with machine learning and real-time prediction systems
    experience with iOS or Android app development
    experience with managing Linux servers, including infrastructure as code (Puppet, Ansible) and containerization


What We Offer


    Office First: Collaboration is easier and more effective in person, which is why we have offices in Geneva, Zurich, Prague, Barcelona, Paris, London, Vilnius, Skopje, and Taipei. You can also enjoy working from home up to 30% of the time, while enjoying great company during our three core days in the office. 
    Technology: We provide all the devices and software you need to excel in your role, ensuring you have the best tools at your disposal to achieve your goals.
    Food: Lunch and snacks are provided by Proton every day at our offices.
    Transport: We will always support our employees with transport costs through subsidizing public transport, bike allowances, or parking spaces based on your office location.
    Stock Options: At Proton, we are all owners of the company and you get stock options when you join us.
    Flexible Working: You can define your own working hours as long as it works with team meetings.
    Learning and Development: We are committed to your professional growth. Proton offers various learning opportunities, including training programs, conferences and events, and continual learning.
    Employee Benefits: Comprehensive health insurance plans, competitive retirement savings options, generous vacation and leave policies, and wellness programs.
    Work that Matters: Proton is a community-first organization, started with the support of a crowdfunding campaign and built with community input. To this day, Proton’s only source of revenue is user subscriptions. Over 100 million people trust and support Proton, and we put our users and community first in everything we do. Read more about our impact here.


Our Commitment to Diversity and Inclusion

At Proton, we believe diversity drives innovation and strengthens our mission to provide privacy as a default for all. We are committed to fostering an inclusive environment where all individuals, regardless of race, ethnicity, gender, age, sexual orientation, physical ability, or socio-economic background, feel valued and empowered. We strive to create equal opportunities, promote open dialogue, and support continuous learning to ensure every voice is heard and respected.

If you need any extra support or reasonable adjustments during the hiring process, please let your talent partner know.

Candidate Privacy Notice

When you apply for a position, refer a candidate, or are considered for a role at Proton Technologies AG (Proton, we, us, or our), your information is stored in Greenhouse, in accordance with their Service Privacy Policy. This information is used to evaluate your suitability for the posted position. We also retain this information for consideration for future roles that you may apply for or that we believe may align with your background and skills.

If we no longer have a legitimate business need to process your information, we will either delete or anonymize it. Should you have any inquiries about how we use or manage your information, or if you wish to access, correct, or delete your data, please contact our privacy team at careers@proton.ch.

Proton does not accept unsolicited resumes from any sources other than directly from candidates. We will not pay a fee for any placement resulting from an unsolicited offer, even if the candidate is subsequently hired by Proton.

To learn more about our privacy policy, please visit our privacy policy page."
# To attach a file, uncomment the FILE_PATH line and the matching -F line below.
# FILE_PATH="/path/to/your/cv.pdf"

response=$(curl -sS -X POST "$URL" \
  -F "text=$TEXT" \
  -F "job_description=$JOB_DESCRIPTION")
  # -F "file=@$FILE_PATH"

printf '\n===== LaTeX =====\n\n'
echo "$response"
