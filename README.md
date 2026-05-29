# Discord Markov Chain Bot

A Discord bot that generates messages using a Markov chain based on chat history. This bot supports slash commands. Inspired by Eliza (RIP).

> Note: this is a funny side project, the bot records messages in `data/channel_data.json` (unidentified) and `data/user_data.json` (identified). Don't use this for weird stuff.

## Features

- Generates messages based on channel or user chat history.
- Commands to enable/disable the bot in a channel.
- Admin settings for generated mentions, links, emojis, and banned words.
- Flush chat history data.

## TO-DO

- [ ] Let the bot parse emojis properly
- [x] Give the bot more admin settings to disable posting links or emojis
- [x] Make the generate command shorter
- [x] Make sure the bot responds to all interactions appropriately. Cleaner error handling.

## Commands

- `/enable` - Enable the bot in the current channel.

  > 💡 The bot will only record messages to history while this option is on.

- `/disable channel` - Disable the bot in the current channel.
- `/disable server` - Disable the bot in all text channels.
  
  > 💡 The bot will keep the channel's history unless explicitly flushed.

- `/settings show` - Show this server's output settings.
- `/settings output` - Toggle whether generated messages can include mentions, links, or emojis.
- `/settings banlist` - Set a comma-separated list of banned words or phrases.
- `/flush channel` - Flush the current channel's chat history from the bot.
- `/flush all` - Flush all recorded chat history from the bot.
- `/generate` - Generate a message using recorded channel chat history.
  - `user` - Generate a message using a user's chat history.
  - `length` - Generate a message with a modified maximum word length (default is 20, max is 100).
- `/gen` - Short alias for `/generate`.

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
        - `applications.commands`
    - Under "Bot Permissions", select:
        - `Send Messages`
        - `Read Message History`
    - Use the generated URL to invite the bot to your Discord server.

4. **Enable Privileged Gateway Intents**:
    - In the "Bot" tab, enable `Message Content Intent`.

### Starting the Bot

1. Clone the repository.
2. Install dependencies.

     ```bash
      pip install -r requirements.txt
     ```

3. Configure the bot token.

    - Set `DISCORD_TOKEN` in the environment, or make a `config.json` file in the project's directory with the following structure:

        ```json
        {
            "token": "{your actual token}"
        }
        ```

4. Run `python3 __main__.py`. If you're hosting this yourself I'm assuming you know how to run it detached. If not then look it up (and please set up a virtual environment).
5. Invite the bot to your server.

## License

MIT License

Copyright (c) 2025 Ever Montes
