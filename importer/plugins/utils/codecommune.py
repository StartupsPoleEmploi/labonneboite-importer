import csv
from os.path import dirname, join
from typing import Dict

CommuneId = str
CommuneName = str


def load_code_commune() -> Dict[CommuneId, CommuneName]:
    path = join(dirname(__file__), 'codecommune.csv')
    file = open(path, 'r', encoding='utf-8')
    csv_reader = csv.reader(file)
    next(csv_reader)
    return dict(csv_reader)


CODE_COMMUNE = load_code_commune()
