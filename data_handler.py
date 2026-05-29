import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


class DataHandler:
    def __init__(self):
        self.channel_file = DATA_DIR / "channel_data.json"
        self.user_file = DATA_DIR / "user_data.json"

        DATA_DIR.mkdir(exist_ok=True)
        for file in [self.channel_file, self.user_file]:
            if not file.exists():
                self._write_json(file, {})

    def _read_json(self, file: Path):
        with open(file, "r") as f:
            return json.load(f)

    def _write_json(self, file: Path, data):
        temp_file = file.with_suffix(f"{file.suffix}.tmp")
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_file, file)

    def add_channel_message(self, channel_id, message):
        data = self._read_json(self.channel_file)
        str_id = str(channel_id)
        if str_id not in data:
            data[str_id] = []
        data[str_id].append(message)
        self._write_json(self.channel_file, data)

    def get_channel_data(self, channel_id):
        data = self._read_json(self.channel_file)
        return data.get(str(channel_id), [])

    def flush_channel(self, channel_id):
        data = self._read_json(self.channel_file)
        data.pop(str(channel_id), None)
        self._write_json(self.channel_file, data)

    def add_user_message(self, user_id, message):
        data = self._read_json(self.user_file)
        str_id = str(user_id)
        if str_id not in data:
            data[str_id] = []
        data[str_id].append(message)
        self._write_json(self.user_file, data)

    def get_user_data(self, user_id):
        data = self._read_json(self.user_file)
        return data.get(str(user_id), [])

    def flush_user(self, user_id):
        data = self._read_json(self.user_file)
        data.pop(str(user_id), None)
        self._write_json(self.user_file, data)

    def flush_all(self):
        self._write_json(self.channel_file, {})
        self._write_json(self.user_file, {})
