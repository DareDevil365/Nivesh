"""Repair known PDF ligature encodings without changing financial punctuation."""

import unicodedata


def repair_pdf_text(text):
    return unicodedata.normalize("NFKC", text).replace("/f_i", "fi").replace("/f_l", "fl")
