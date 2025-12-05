import spacy

# FIXME: Use the transformer-based models instead
# (grc_perseus_lg is making mistakes with the first declension)
grc_nlp = spacy.load("grc_perseus_lg")
lat_nlp = spacy.load("la_core_web_lg")

DISABLED_PIPES = ["parser", "ner", "textcat"]

def nlp_grc(texts: list[str]):
    return list(grc_nlp.pipe(texts, disable=DISABLED_PIPES))


def nlp_lat(texts: list[str]):
    return list(lat_nlp.pipe(texts, disable=DISABLED_PIPES))
