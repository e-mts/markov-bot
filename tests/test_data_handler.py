import json
import tempfile
import unittest
from datetime import datetime, timezone

from data_handler import DataHandler


class DataHandlerTests(unittest.TestCase):
    def test_channel_data_can_exclude_user_records(self):
        with tempfile.TemporaryDirectory() as data_dir:
            handler = DataHandler(data_dir=data_dir)

            timestamp = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)

            handler.add_channel_message(123, 10, "keep me", timestamp=timestamp)
            handler.add_channel_message(123, 20, "skip me", timestamp=timestamp)

            self.assertEqual(
                handler.get_channel_data(123, excluded_user_ids={20}),
                ["keep me"],
            )

            stored = json.loads(handler.channel_file.read_text())
            self.assertEqual(
                stored["123"][0],
                {
                    "user_id": "10",
                    "message": "keep me",
                    "timestamp": "2026-05-29T12:00:00Z",
                },
            )

    def test_user_data_is_stored_with_timestamp_metadata(self):
        with tempfile.TemporaryDirectory() as data_dir:
            handler = DataHandler(data_dir=data_dir)
            timestamp = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)

            handler.add_user_message(10, "user memory", timestamp=timestamp)

            self.assertEqual(handler.get_user_data(10), ["user memory"])
            stored = json.loads(handler.user_file.read_text())
            self.assertEqual(
                stored["10"][0],
                {
                    "message": "user memory",
                    "timestamp": "2026-05-29T12:00:00Z",
                },
            )

    def test_legacy_string_records_still_read_as_messages(self):
        with tempfile.TemporaryDirectory() as data_dir:
            handler = DataHandler(data_dir=data_dir)
            handler._write_json(handler.channel_file, {"123": ["old channel message"]})
            handler._write_json(handler.user_file, {"10": ["old user message"]})

            self.assertEqual(handler.get_channel_data(123), ["old channel message"])
            self.assertEqual(handler.get_user_data(10), ["old user message"])

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
