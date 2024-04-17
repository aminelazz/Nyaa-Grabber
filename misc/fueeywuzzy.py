from fuzzywuzzy import process
from fuzzywuzzy import fuzz

def get_closest_match(query, choices):
    match = process.extractBests(query=query, choices=choices, score_cutoff=80)
    # if score < 75:
    #     return None
    return match

query = "Nanatsu no Taizai: Mokushiroku no Yonkishi The Seven Deadly Sins: Four Knights of the Apocalypse"
choices = [
    "Nanatsu no Taizai Mokushiroku no Yonkishi S01E04 THE DEMON OF ECHO GORGE 1080p NF WEB-DL AAC2.0 H 264-VARYG (Seven Deadly Sins: Four Knights of the Apocalypse)",
    "[Passerby] Nanatsu no Taizai: Mokushiroku no Yonkishi (The Seven Deadly Sins: Four Knights of the Apocalypse) - 05 [49304C64].mkv",
    "[Erai-raws] Nanatsu no Taizai - Fundo no Shinpan - 01 ~ 24 [1080p][Multiple Subtitle] [ENG][POR-BR][SPA-LA][SPA][ARA][FRE][GER][ITA][RUS][JPN][POR][POL][DUT][NOB][FIN][TUR][SWE][GRE][HEB][RUM][IND][THA][KOR][DAN][CHI][VIE][UKR][HUN][CES][HRV][MAY]"
]

# print(get_closest_match(query, choices))

# Check the similarity score
name = "Sokushi Cheat"
full_name = "[SubsPlease] Sokushi Cheat - 01 (1080p) [E47853A6].mkv"

print(f"Token sort ratio similarity score: {fuzz.token_set_ratio(name, full_name)}")

"""
Token sort ratio similarity score: 100
"""