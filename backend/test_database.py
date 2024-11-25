import unittest
import os

from servicioAlmacenamiento.database import save_user, get_user, save_message, get_messages, init_db, DB_NAME

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)
init_db()

class TestDatabase(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_save_user(self):
        save_user("test_user", "password123")
        user = get_user("test_user")
        self.assertIsNotNone(user)
        self.assertTrue(user["password_hash"] == "password123")

    def test_save_message(self):
        save_message("test_user", "receiver", "Hello!")
        messages = get_messages("receiver")
        self.assertIn("Hello!", messages)

if __name__ == "__main__":
    unittest.main()
