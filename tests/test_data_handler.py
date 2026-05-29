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

            handler.add_user_message(
                10,
                123,
                "user memory",
                timestamp=timestamp,
                guild_id=999,
            )

            self.assertEqual(handler.get_user_data(10), ["user memory"])
            self.assertEqual(handler.get_user_data(10, guild_id=999), ["user memory"])
            stored = json.loads(handler.user_file.read_text())
            self.assertEqual(
                stored["10"][0],
                {
                    "guild_id": "999",
                    "channel_id": "123",
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
            self.assertEqual(handler.get_user_data(10, guild_id=999), [])

    def test_user_data_can_be_scoped_to_guild(self):
        with tempfile.TemporaryDirectory() as data_dir:
            handler = DataHandler(data_dir=data_dir)

            handler.add_user_message(10, 123, "guild one", guild_id=1)
            handler.add_user_message(10, 456, "guild two", guild_id=2)
            handler.add_user_message(10, 789, "legacy shape")

            self.assertEqual(handler.get_user_data(10, guild_id=1), ["guild one"])
            self.assertEqual(handler.get_user_data(10, guild_id=2), ["guild two"])
            self.assertEqual(
                handler.get_user_data(10),
                ["guild one", "guild two", "legacy shape"],
            )

    def test_flush_user_removes_user_and_channel_records(self):
        with tempfile.TemporaryDirectory() as data_dir:
            handler = DataHandler(data_dir=data_dir)

            handler.add_user_message(10, 123, "user memory", guild_id=999)
            handler.add_channel_message(123, 10, "remove me")
            handler.add_channel_message(123, 20, "keep me")

            handler.flush_user(10)

            self.assertEqual(handler.get_user_data(10), [])
            self.assertEqual(handler.get_channel_data(123), ["keep me"])

    def test_flush_channel_removes_matching_user_records(self):
        with tempfile.TemporaryDirectory() as data_dir:
            handler = DataHandler(data_dir=data_dir)

            handler.add_channel_message(123, 10, "channel memory")
            handler.add_user_message(10, 123, "remove me", guild_id=999)
            handler.add_user_message(10, 456, "keep me", guild_id=999)
            user_data = handler._read_json(handler.user_file)
            user_data["10"].append("legacy")
            handler._write_json(handler.user_file, user_data)

            handler.flush_channel(123)

            self.assertEqual(handler.get_channel_data(123), [])
            self.assertEqual(handler.get_user_data(10), ["keep me", "legacy"])


if __name__ == "__main__":
    unittest.main()
