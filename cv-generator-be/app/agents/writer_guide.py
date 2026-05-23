"""The CV-writing style guide injected into the WriterAgent system prompt."""

CV_GUIDE = r"""# SWE CV rules (operative)

Write plain, evidence-dense, role-tailored bullets that prove engineering impact with metrics, scope, and concrete technical decisions. Quality over quantity: a shorter CV of strong bullets beats a padded one — the reader judges the CV by its weakest lines, so every line must earn its place.

## Bullets
- Fragments, not prose. Lead with a strong past-tense verb (Built, Designed, Migrated, Reduced, Automated, Optimized). No pronouns (I, we, my team). Avoid résumé theater (spearheaded, leveraged, revolutionized).
- Front-load the metric, then the action: *Improved [metric] from [before] to [after] by [technical action].* When exact numbers are confidential or absent, use %, ranges, or before/after.
- One line is ideal; two only when the substance needs it. Never pad to fill a line.
- Cut filler: "worked on", "helped with", "responsible for", "various", "fast-paced", "passionate", "team player".
- Specify your part; don't claim team-wide outcomes as your own.
- Use industry terms (Kafka, p95, idempotency), not internal product/project names.

Weak: Worked on backend infrastructure.
Strong: Cut failed production deploys from 7/month to 2/month by adding Terraform-managed service config and CI/CD validation across 14 services.

## Tailoring
Translate real experience into the posting's vocabulary — don't keyword-stuff. Surface the technologies a role names inside concrete impact bullets, not just in the skills list.

## Sections
- Summary: 1-3 lines characterizing the candidate (level, focus, headline stack). Not a list of achievements; never "passionate ... seeking ...".
- Experience: most-relevant / most-recent first; strongest bullet first; 3-5 bullets for recent roles, 1-3 for older. No generic duty bullets.
- Skills: grouped, truthful, strongest first. Don't list every tool ever touched; for seniors, skills support experience, they don't replace it.
- Education: brief; top of CV for new grads, below experience otherwise. Trim coursework to a few role-relevant items.
- Projects: deployed / used / benchmarked / OSS only — they matter most for interns and new grads. Awards, research, and publications only if role-relevant.

## Tier focus
- New grad: CS fundamentals plus finished, deployed projects; education first.
- Mid-level: ownership of a feature/service, production debugging, shipping without supervision.
- Senior+: fewer, stronger bullets — scope, architecture, cross-team influence, migrations, tradeoffs.

## Never include
Objective statements; photos; age / marital status / full address; "References available on request"; skill bars; soft-skill claims; untranslated internal acronyms; tools you cannot explain; inflated or undefendable metrics; "Familiar with" lists that dilute stronger skills.
"""
