# Discord Markov Chain Bot

A Discord bot that generates messages using a Markov chain based on chat history. This bot supports slash commands. Inspire by Eliza (RIP).

> Note: this is a funny side project, the bot records messages in `data/channel_data.json` (unidentified) and `data/user_data.json` (identified). Don't use this for weird stuff.

## Features

- Generates messages based on channel or user chat history.
- Commands to enable/disable the bot in a channel.
- Flush chat history data.

## Commands

- `/enable` - Enable the bot in the current channel.

  > 💡 The bot will only record messages to history while this option is on.

- `/disable` - Disable the bot in the current channel/server.
  
  > 💡 The bot will keep the channel's history unless explicity flushed.

- `/flush` - Flush the current channel/server chat history from the bot.
- `/generate` - Generate a message using all recorded chat history.
  - `/generate user` - Generates a message using a user's chat history.
  - `/generate length` - Generate a message with a modified Markov chain length (default is 20, max is 100).

## Setup

### Create a Discord Application and Bot

1. **Create a Discord Application**:
    - Go to the [Discord Developer Portal](https://discord.com/developers/applications).
    - Click on "New Application" and give it a name.

2. **Add a Bot to the Application**:
    - In your application's settings, navigate to the "Bot" tab.
    - Click "Add Bot" and confirm.
    - Copy the **Bot Token**.❗❗**Do not share this token**❗❗.

3. **Set Bot Permissions**:
    - Under the "OAuth2" tab, navigate to "URL Generator".
    - Select the following scopes:
        - `bot`
    - Under "Bot Permissions", select:
        - `Send Messages`
        - `Read Message History`
        - `Manage Messages` (if needed for flushing data)
    - Use the generated URL to invite the bot to your Discord server.

### Starting the Bot

1. Clone the repository.
2. Install dependencies.

     ```bash
      pip install -r requirements.txt
     ```

3. Configure the bot token.

    - Make a `config.json` file in the project's directory with the following structure:

        ```json
        {
            "token": "{your actual token}"
        }
        ```

4. Run ``__main.py__``. If you're hosting this yourself I'm assuming you know how to run it detached. If not then look it up (and please set up a virtual environment).
5. Invite the bot to your server.

## License

MIT License

Copyright (c) 2025 Ever Montes
