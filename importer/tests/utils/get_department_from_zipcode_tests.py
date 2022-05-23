import unittest

from utils.get_departement_from_zipcode import get_department_from_zipcode


class GetDepartmentFromZipcodeTestCase(unittest.TestCase):

    def test_get_department_from_zipcode(self):
        department = get_department_from_zipcode("6600")
        self.assertEqual(department, "06")


if __name__ == '__main__':
    unittest.main()
