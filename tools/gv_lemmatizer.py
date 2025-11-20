import spacy

grc_nlp = spacy.load("grc_perseus_lg")
lat_nlp = spacy.load("la_core_web_lg")

DISABLED_PIPES = ["parser", "ner", "textcat"]

def lemmatize_grc(s: str):
    return grc_nlp(s, disable=DISABLED_PIPES)


def lemmatize_lat(s: str):
    return lat_nlp(s, disable=DISABLED_PIPES)
