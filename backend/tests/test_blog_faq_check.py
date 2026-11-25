"""The generator's FAQ check must match what the site turns into FAQPage JSON-LD."""
from services.blog_generator import faq_questions


def test_reads_questions_until_next_h2():
    body = "Intro\n\n## Frequently Asked Questions\n\n### One?\nA.\n\n### Two?\nB.\n\n## Sources\n\n### Not a question\n"
    assert faq_questions(body) == ["One?", "Two?"]


def test_accepts_faq_heading_variants():
    assert faq_questions("## FAQs\n### Q?\nA") == ["Q?"]
    assert faq_questions("## frequently asked questions\n### Q?\nA") == ["Q?"]


def test_missing_section_or_bold_questions_dont_count():
    assert faq_questions("We get many frequently asked questions.\n### Q?\nA") == []
    assert faq_questions("## Frequently asked questions\n**Q?** A") == []
