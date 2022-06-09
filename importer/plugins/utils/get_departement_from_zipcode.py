from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=128 * 1024)
def get_department_from_zipcode(zipcode: Optional[str]) -> Optional[str]:
    zipcode = str(zipcode).strip() if zipcode else ""

    if len(zipcode) == 1:
        department = "0%s" % zipcode[0]
    elif len(zipcode) == 2:
        department = zipcode
    elif len(zipcode) == 4:
        department = "0%s" % zipcode[0]
    elif len(zipcode) == 5:
        department = zipcode[:2]
    else:
        department = None

    if department in ["2A", "2B"]:  # special case of Corsica
        department = "20"
    return department
