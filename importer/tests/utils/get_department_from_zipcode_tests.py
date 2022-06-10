import unittest

from utils.get_departement_from_zipcode import get_department_from_zipcode


class GetDepartmentFromZipcodeTestCase(unittest.TestCase):

    def test_get_department_from_zipcode(self):
        department = get_department_from_zipcode("")
        self.assertEqual(department, None, "Empty zipcode should return None")

        department = get_department_from_zipcode(None)
        self.assertEqual(department, None, "None zipcode should return None")

        department = get_department_from_zipcode("6")
        self.assertEqual(department, "06")

        department = get_department_from_zipcode("06")
        self.assertEqual(department, "06")

        department = get_department_from_zipcode("06000")
        self.assertEqual(department, "06")

        department = get_department_from_zipcode("6000")
        self.assertEqual(department, "06")

        department = get_department_from_zipcode("2A")
        self.assertEqual(department, "20", "Corsica should be group in the old department format")


if __name__ == '__main__':
    unittest.main()
