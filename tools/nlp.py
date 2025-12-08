import spacy

# FIXME: Use the transformer-based models instead
# (grc_perseus_lg is making mistakes with the first declension)
grecy = spacy.load("grc_perseus_lg")
latincy = spacy.load("la_core_web_lg")

DISABLED_PIPES = ["parser", "ner", "textcat"]

grecy_tokenizer = grecy.tokenizer
latincy_tokenizer = latincy.tokenizer


def nlp_grc(texts: list[str]):
    return list(grecy.pipe(texts, disable=DISABLED_PIPES))


def nlp_lat(texts: list[str]):
    return list(latincy.pipe(texts, disable=DISABLED_PIPES))
