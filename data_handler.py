# data_handler.py

import json
import os

class DataHandler:
    def __init__(self):
        self.channel_file = 'data/channel_data.json'
        self.user_file = 'data/user_data.json'

        # Initialize files if they don't exist
        if not os.path.exists('data'):
            os.makedirs('data')
        
        for file in [self.channel_file, self.user_file]:
            if not os.path.exists(file):
                with open(file, 'w') as f:
                    json.dump({}, f)

    def add_channel_message(self, channel_id, message):
        with open(self.channel_file, 'r') as f:
            data = json.load(f)
        str_id = str(channel_id)
        if str_id not in data:
            data[str_id] = []
        data[str_id].append(message)
        with open(self.channel_file, 'w') as f:
            json.dump(data, f, indent=4)

    def get_channel_data(self, channel_id):
        with open(self.channel_file, 'r') as f:
            data = json.load(f)
        return data.get(str(channel_id), [])

    def flush_channel(self, channel_id):
        with open(self.channel_file, 'r') as f:
            data = json.load(f)
        data.pop(str(channel_id), None)
        with open(self.channel_file, 'w') as f:
            json.dump(data, f, indent=4)

    def add_user_message(self, user_id, message):
        with open(self.user_file, 'r') as f:
            data = json.load(f)
        str_id = str(user_id)
        if str_id not in data:
            data[str_id] = []
        data[str_id].append(message)
        with open(self.user_file, 'w') as f:
            json.dump(data, f, indent=4)

    def get_user_data(self, user_id):
        with open(self.user_file, 'r') as f:
            data = json.load(f)
        return data.get(str(user_id), [])

    def flush_user(self, user_id):
        with open(self.user_file, 'r') as f:
            data = json.load(f)
        data.pop(str(user_id), None)
        with open(self.user_file, 'w') as f:
            json.dump(data, f, indent=4)