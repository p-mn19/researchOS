from app.services.pdf_parser import extract_authors_from_front_matter


def test_extracts_authors_from_the_first_page_title_block():
    text = """
    A Reliable Method for ResearchOS
    Alice B. Smith1, Bob Jones2 and Chandra K. Patel1
    1 Department of Computer Science, Example University
    alice@example.edu

    Abstract
    This paper evaluates a method.
    """

    assert extract_authors_from_front_matter(text) == [
        "Alice B. Smith",
        "Bob Jones",
        "Chandra K. Patel",
    ]


def test_does_not_treat_affiliations_or_abstract_as_authors():
    text = """
    Research Paper Title
    Department of Computer Science
    Example University

    Abstract
    Alice Smith proposed the method in this paper.
    """

    assert extract_authors_from_front_matter(text) == []


def test_does_not_treat_a_title_cased_title_as_an_author():
    text = """
    Deep Learning
    Alice Smith and Bob Jones

    Abstract
    This paper evaluates a method.
    """

    assert extract_authors_from_front_matter(text) == [
        "Alice Smith",
        "Bob Jones",
    ]
