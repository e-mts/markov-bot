import discord
from discord import app_commands
import json
import os

from markov_chain import MarkovChain
from data_handler import DataHandler

# TODO: Use asyncio to handle ALL of the tasks

# Load configuration
with open('config.json') as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Create command groups


class DisableCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="disable", description="Disable bot functionality")

    @app_commands.command(name="channel", description="Disable the bot in the current channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel(self, interaction: discord.Interaction):
        bot_name = interaction.client.user.name  # type: ignore
        bot.enabled_channels.discard(interaction.channel_id)
        bot.save_settings()
        await interaction.response.send_message(f"{bot_name} has been disabled in this channel.")

    @app_commands.command(name="server", description="Disable the bot in all channels")
    @app_commands.checks.has_permissions(administrator=True)
    async def server(self, interaction: discord.Interaction):
        bot_name = interaction.client.user.name  # type: ignore
        for channel in interaction.guild.text_channels:  # type: ignore
            bot.enabled_channels.discard(channel.id)
        bot.save_settings()
        await interaction.response.send_message(f"{bot_name} has been disabled in all channels.")


class FlushCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="flush", description="Flush bot memories")

    @app_commands.command(name="channel", description="Flush memories for current channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel(self, interaction: discord.Interaction):
        bot.data_handler.flush_channel(interaction.channel_id)
        bot.markov_chains.pop(interaction.channel_id, None)
        await interaction.response.send_message("Flushed all memories for this channel.", ephemeral=True)

    @app_commands.command(name="all", description="Flush all of the bot's memories")
    @app_commands.checks.has_permissions(administrator=True)
    async def server(self, interaction: discord.Interaction):
        with open(bot.data_handler.channel_file, 'w') as f:
            json.dump({}, f, indent=4)
        with open(bot.data_handler.user_file, 'w') as f:
            json.dump({}, f, indent=4)
        bot.markov_chains.clear()
        await interaction.response.send_message("Flushed all memories.", ephemeral=True)


class GenerateCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="generate", description="Generate messages")

    @app_commands.command(name="message", description="Generate a message")
    @app_commands.describe(
        user="Optional: Mention a user to generate a message based on their data.",
        length="Optional: Specify the maximum length of the generated message (default is 20, max is 100)."
    )
    async def message(self, interaction: discord.Interaction, user: discord.User = None, length: int = 20):  # type: ignore
        try:
            # Validate length
            max_allowed_length = 100  # Set the maximum length
            if length < 1 or length > max_allowed_length:
                await interaction.response.send_message(
                    f"Length must be a positive number between 1 and {
                        max_allowed_length}.",
                    ephemeral=True
                )
                return

            if user:  # Generate a message for the specified user
                if user.id not in bot.markov_chains:
                    user_data = bot.data_handler.get_user_data(user.id)
                    if not user_data:
                        await interaction.response.send_message(
                            f"Not enough data to generate a message for {
                                user.name}.",
                            ephemeral=True
                        )
                        return
                    bot.markov_chains[user.id] = MarkovChain()
                    bot.markov_chains[user.id].build_model(user_data)

                # Generate the message
                generated = bot.markov_chains[user.id].generate_sentence(
                    max_length=length)
                if not generated:  # If the generated message is empty or None
                    await interaction.response.send_message(
                        f"Not enough data to generate a message for {
                            user.name}.",
                        ephemeral=True
                    )
                    return

                await interaction.response.send_message(generated)

            else:  # Default behavior: generate a message for the current channel
                if interaction.channel_id not in bot.markov_chains:
                    data = bot.data_handler.get_channel_data(
                        interaction.channel_id)
                    if not data:
                        await interaction.response.send_message(
                            "Not enough data to generate a message for this channel.",
                            ephemeral=True
                        )
                        return
                    bot.markov_chains[interaction.channel_id] = MarkovChain()
                    bot.markov_chains[interaction.channel_id].build_model(data)

                # Generate the message
                generated = bot.markov_chains[interaction.channel_id].generate_sentence(
                    max_length=length)
                if not generated:  # If the generated message is empty or None
                    await interaction.response.send_message(
                        "Not enough data to generate a message for this channel.",
                        ephemeral=True
                    )
                    return

                await interaction.response.send_message(generated)

        except Exception as e:
            # Catch any unexpected exceptions
            await interaction.response.send_message(
                "An unexpected error occurred while generating the message. Please try again later.",
                ephemeral=True
            )


class EnableCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="enable", description="Enable bot functionality")

    @app_commands.command(name="channel", description="Enable the bot in the current channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel(self, interaction: discord.Interaction):
        bot_name = interaction.client.user.name  # type: ignore
        bot.enabled_channels.add(interaction.channel_id)
        bot.save_settings()
        await interaction.response.send_message(f"{bot_name} enabled in this channel.")


class MarkovBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        os.makedirs('data', exist_ok=True)
        self.tree = app_commands.CommandTree(self)
        self.data_handler = DataHandler()
        self.markov_chains = {}  # Dictionary to hold Markov chains per channel/user
        self.enabled_channels = set()

        # Add command groups
        self.tree.add_command(DisableCommands())
        self.tree.add_command(FlushCommands())
        self.tree.add_command(EnableCommands())
        self.tree.add_command(GenerateCommands())

    async def setup_hook(self):
        await self.tree.sync()  # Sync slash commands with Discord
        print(f'Synced commands to Discord.')

    async def on_ready(self):
        print(f'Logged in as {self.user.name}')  # type: ignore
        self.load_settings()

    def load_settings(self):
        settings_file = 'data/settings.json'
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                self.enabled_channels.update(
                    settings.get("enabled_channels", []))
        else:
            settings = {"enabled_channels": []}
            with open(settings_file, 'w') as f:
                json.dump(settings, f)

    def save_settings(self):
        settings_file = 'data/settings.json'
        with open(settings_file, 'w') as f:
            json.dump({"enabled_channels": list(
                self.enabled_channels)}, f, indent=4)

    async def on_message(self, message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Only process messages in enabled channels
        if message.channel.id in self.enabled_channels:
            # Store message content
            self.data_handler.add_channel_message(
                message.channel.id, message.content)
            self.data_handler.add_user_message(
                message.author.id, message.content)

            # Update Markov chains if they exist
            if message.channel.id in self.markov_chains:
                self.markov_chains[message.channel.id].add_text(
                    message.content)
            if message.author.id in self.markov_chains:
                self.markov_chains[message.author.id].add_text(message.content)

if __name__ == '__main__':
    bot = MarkovBot()
    bot.run(config['token'])
