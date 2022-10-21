import csv


class SemiColonDialect(csv.unix_dialect):
    delimiter = ";"