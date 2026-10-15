from app.services.latex_compile_service import build_complete_document


def test_ieee_fragment_uses_editable_paper_front_matter():
    document = build_complete_document(
        r"\section{Introduction}\nPaper content.",
        document_format="ieee",
    )

    assert r"\title{A Research Study on [Research Topic]}" in document
    assert document.count(r"\IEEEauthorblockN{[Author Name]}") == 2
    assert r"\begin{abstract}" in document
    assert r"\begin{IEEEkeywords}" in document


def test_normal_fragment_does_not_receive_ieee_front_matter():
    document = build_complete_document(
        r"\section{Introduction}\nPaper content.",
        document_format="normal",
    )

    assert r"\documentclass[12pt,a4paper]{article}" in document
    assert r"\begin{IEEEkeywords}" not in document
    assert r"\title{A Research Study on [Research Topic]}" in document
    assert r"\author{[Author Name]" in document
