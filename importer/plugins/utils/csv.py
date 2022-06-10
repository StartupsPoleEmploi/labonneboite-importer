import csv


class SemiColonDialect(csv.unix_dialect):
    delimiter = ";"


class UnquotedDialect(csv.unix_dialect):
    quoting = csv.QUOTE_NONE


class UnquotedSemiColonDialect(SemiColonDialect, UnquotedDialect):
    pass
