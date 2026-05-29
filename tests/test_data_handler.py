import tempfile
import unittest

from data_handler import DataHandler


class DataHandlerTests(unittest.TestCase):
    def test_channel_data_can_exclude_user_records(self):
        with tempfile.TemporaryDirectory() as data_dir:
            handler = DataHandler(data_dir=data_dir)

            handler.add_channel_message(123, 10, "keep me")
            handler.add_channel_message(123, 20, "skip me")

            self.assertEqual(
                handler.get_channel_data(123, excluded_user_ids={20}),
                ["keep me"],
            )

    def test_flush_user_removes_user_and_channel_records(self):
        with tempfile.TemporaryDirectory() as data_dir:
            handler = DataHandler(data_dir=data_dir)

            handler.add_user_message(10, "user memory")
            handler.add_channel_message(123, 10, "remove me")
            handler.add_channel_message(123, 20, "keep me")

            handler.flush_user(10)

            self.assertEqual(handler.get_user_data(10), [])
            self.assertEqual(handler.get_channel_data(123), ["keep me"])


if __name__ == "__main__":
    unittest.main()
