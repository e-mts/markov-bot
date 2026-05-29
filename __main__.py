import json
import os
import re
import traceback
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

import discord
from discord import app_commands

from markov_chain import MarkovChain
from data_handler import DataHandler


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = BASE_DIR / "config.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
DISCORD_MESSAGE_LIMIT = 2000
MAX_GENERATION_RETRIES = 10

DEFAULT_GUILD_SETTINGS = {
    "allow_user_mentions": True,
    "allow_role_mentions": True,
    "allow_everyone_mentions": True,
    "allow_links": True,
    "allow_emojis": True,
    "banned_words": [],
}

URL_PATTERN = re.compile(r"(?:https?://|www\.|discord\.gg/)", re.IGNORECASE)
USER_MENTION_PATTERN = re.compile(r"<@!?\d+>")
ROLE_MENTION_PATTERN = re.compile(r"<@&\d+>")
EVERYONE_MENTION_PATTERN = re.compile(r"@everyone|@here", re.IGNORECASE)
CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
UNICODE_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u27BF"
    "]"
)

def load_config() -> dict[str, str]:
    token = os.getenv("DISCORD_TOKEN")
    if token:
        return {"token": token}

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    raise RuntimeError("Set DISCORD_TOKEN or create config.json with a token.")


def write_json_atomic(file: Path, data: Any):
    temp_file = file.with_suffix(f"{file.suffix}.tmp")
    with open(temp_file, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(temp_file, file)


config = load_config()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True


def parse_banned_words(words: Optional[str]) -> list[str]:
    if not words:
        return []

    return sorted(
        {
            word.strip().lower()
            for word in re.split(r"[,\n]+", words)
            if word.strip()
        }
    )


def normalize_guild_settings(settings: Optional[dict[str, Any]]) -> dict[str, Any]:
    normalized = deepcopy(DEFAULT_GUILD_SETTINGS)
    if not isinstance(settings, dict):
        return normalized

    legacy_allow_mentions = settings.get("allow_mentions")
    for key in (
        "allow_user_mentions",
        "allow_role_mentions",
        "allow_everyone_mentions",
    ):
        if key in settings:
            normalized[key] = bool(settings[key])
        elif legacy_allow_mentions is not None:
            normalized[key] = bool(legacy_allow_mentions)

    for key in ("allow_links", "allow_emojis"):
        if key in settings:
            normalized[key] = bool(settings[key])

    banned_words = settings.get("banned_words", [])
    if isinstance(banned_words, list):
        normalized["banned_words"] = sorted(
            {
                str(word).strip().lower()
                for word in banned_words
                if str(word).strip()
            }
        )

    return normalized


def normalize_user_ids(user_ids: list[Any]) -> set[int]:
    normalized = set()
    for user_id in user_ids:
        try:
            normalized.add(int(user_id))
        except (TypeError, ValueError):
            continue
    return normalized


def setting_state(enabled: bool) -> str:
    return "on" if enabled else "off"


def format_settings(settings: dict[str, Any]) -> str:
    banned_words = settings["banned_words"]
    word_filter = ", ".join(banned_words) if banned_words else "none"
    return (
        f"User mentions: {setting_state(settings['allow_user_mentions'])}\n"
        f"Role mentions: {setting_state(settings['allow_role_mentions'])}\n"
        f"@here/@everyone: {setting_state(settings['allow_everyone_mentions'])}\n"
        f"Links: {setting_state(settings['allow_links'])}\n"
        f"Emojis: {setting_state(settings['allow_emojis'])}\n"
        f"Word filter: {word_filter}"
    )


def truncate_for_discord(message: str) -> str:
    if len(message) <= DISCORD_MESSAGE_LIMIT:
        return message

    truncated = message[: DISCORD_MESSAGE_LIMIT - 3].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return f"{truncated}..."


def contains_banned_word(message: str, banned_words: list[str]) -> bool:
    normalized = message.lower()
    for word in banned_words:
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", normalized):
            return True
    return False


def filter_reasons(message: str, settings: dict[str, Any]) -> list[str]:
    reasons = []
    if not settings["allow_user_mentions"] and USER_MENTION_PATTERN.search(message):
        reasons.append("user mentions")
    if not settings["allow_role_mentions"] and ROLE_MENTION_PATTERN.search(message):
        reasons.append("role mentions")
    if not settings["allow_everyone_mentions"] and EVERYONE_MENTION_PATTERN.search(message):
        reasons.append("@here/@everyone")
    if not settings["allow_links"] and URL_PATTERN.search(message):
        reasons.append("links")
    if not settings["allow_emojis"] and (
        CUSTOM_EMOJI_PATTERN.search(message) or UNICODE_EMOJI_PATTERN.search(message)
    ):
        reasons.append("emojis")
    if contains_banned_word(message, settings["banned_words"]):
        reasons.append("word filter")
    return reasons


def allowed_mentions_for(settings: dict[str, Any]) -> discord.AllowedMentions:
    return discord.AllowedMentions(
        everyone=settings["allow_everyone_mentions"],
        users=settings["allow_user_mentions"],
        roles=settings["allow_role_mentions"],
        replied_user=False,
    )


def user_chain_key(guild_id: int, user_id: int) -> str:
    return f"user:{guild_id}:{user_id}"


def can_manage_settings(interaction: discord.Interaction) -> bool:
    permissions = interaction.permissions
    if permissions.administrator or permissions.manage_guild:
        return True

    raise app_commands.MissingPermissions(["administrator", "manage_guild"])


def settings_permissions_check():
    return app_commands.check(can_manage_settings)


async def reply(
    interaction: discord.Interaction,
    message: str,
    *,
    ephemeral: bool = False,
    allowed_mentions: Optional[discord.AllowedMentions] = None,
):
    if interaction.response.is_done():
        await interaction.followup.send(
            message,
            ephemeral=ephemeral,
            allowed_mentions=allowed_mentions,
        )
        return

    await interaction.response.send_message(
        message,
        ephemeral=ephemeral,
        allowed_mentions=allowed_mentions,
    )


class EnableSettingsCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="enable", description="Enable bot functionality")

    @app_commands.command(name="channel", description="Enable the bot in the current channel")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def channel(self, interaction: discord.Interaction):
        bot_name = interaction.client.user.name  # type: ignore[union-attr]
        bot.enabled_channels.add(interaction.channel_id)
        bot.save_settings()
        await reply(interaction, f"{bot_name} enabled in this channel.")


class DisableSettingsCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="disable", description="Disable bot functionality")

    @app_commands.command(name="channel", description="Disable the bot in the current channel")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def channel(self, interaction: discord.Interaction):
        bot_name = interaction.client.user.name  # type: ignore[union-attr]
        bot.enabled_channels.discard(interaction.channel_id)
        bot.save_settings()
        await reply(interaction, f"{bot_name} has been disabled in this channel.")

    @app_commands.command(name="server", description="Disable the bot in all text channels")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def server(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await reply(interaction, "This command can only be used in a server.", ephemeral=True)
            return

        bot_name = interaction.client.user.name  # type: ignore[union-attr]
        for channel in interaction.guild.text_channels:
            bot.enabled_channels.discard(channel.id)
        bot.save_settings()
        await reply(interaction, f"{bot_name} has been disabled in all text channels.")


class FlushSettingsCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="flush", description="Flush bot memories")

    @app_commands.command(name="channel", description="Flush memories for the current channel")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def channel(self, interaction: discord.Interaction):
        bot.data_handler.flush_channel(interaction.channel_id)
        bot.markov_chains.clear()
        await reply(interaction, "Flushed all memories for this channel.", ephemeral=True)

    @app_commands.command(name="all", description="Flush all bot memories")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def all(self, interaction: discord.Interaction):
        bot.data_handler.flush_all()
        bot.markov_chains.clear()
        await reply(interaction, "Flushed all memories.", ephemeral=True)


class WordFilterSettingsCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="word-filter", description="Configure filtered words")

    @app_commands.command(name="show", description="Show filtered words for generated output")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def show(self, interaction: discord.Interaction):
        settings = bot.get_guild_settings(interaction.guild_id)
        banned_words = settings["banned_words"]
        word_filter = ", ".join(banned_words) if banned_words else "none"
        await reply(interaction, f"Word filter: {word_filter}", ephemeral=True)

    @app_commands.command(name="add", description="Add words or phrases to the output filter")
    @app_commands.describe(words="Comma-separated words or phrases to filter.")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def add(self, interaction: discord.Interaction, words: str):
        settings = bot.get_guild_settings(interaction.guild_id)
        banned_words = set(settings["banned_words"])
        banned_words.update(parse_banned_words(words))
        settings["banned_words"] = sorted(banned_words)
        bot.set_guild_settings(interaction.guild_id, settings)
        await reply(interaction, format_settings(settings), ephemeral=True)

    @app_commands.command(name="remove", description="Remove words or phrases from the output filter")
    @app_commands.describe(words="Comma-separated words or phrases to remove.")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def remove(self, interaction: discord.Interaction, words: str):
        settings = bot.get_guild_settings(interaction.guild_id)
        banned_words = set(settings["banned_words"])
        banned_words.difference_update(parse_banned_words(words))
        settings["banned_words"] = sorted(banned_words)
        bot.set_guild_settings(interaction.guild_id, settings)
        await reply(interaction, format_settings(settings), ephemeral=True)

    @app_commands.command(name="clear", description="Clear the word filter")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def clear_words(self, interaction: discord.Interaction):
        settings = bot.get_guild_settings(interaction.guild_id)
        settings["banned_words"] = []
        bot.set_guild_settings(interaction.guild_id, settings)
        await reply(interaction, format_settings(settings), ephemeral=True)


class SettingsCommands(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="settings",
            description="Configure bot settings",
            default_permissions=discord.Permissions(manage_guild=True),
        )
        self.add_command(EnableSettingsCommands())
        self.add_command(DisableSettingsCommands())
        self.add_command(FlushSettingsCommands())
        self.add_command(WordFilterSettingsCommands())

    @app_commands.command(name="show", description="Show this server's output settings")
    @settings_permissions_check()
    @app_commands.guild_only()
    async def show(self, interaction: discord.Interaction):
        settings = bot.get_guild_settings(interaction.guild_id)
        await reply(interaction, format_settings(settings), ephemeral=True)

    @app_commands.command(name="pings", description="Toggle generated ping filters")
    @app_commands.rename(
        user_mentions="users",
        role_mentions="roles",
        everyone_mentions="everyone",
    )
    @app_commands.describe(
        mentions="Allow or block all generated pings at once.",
        user_mentions="Allow generated messages to mention users.",
        role_mentions="Allow generated messages to mention roles.",
        everyone_mentions="Allow generated messages to use @here or @everyone.",
    )
    @settings_permissions_check()
    @app_commands.guild_only()
    async def pings(
        self,
        interaction: discord.Interaction,
        mentions: Optional[bool] = None,
        user_mentions: Optional[bool] = None,
        role_mentions: Optional[bool] = None,
        everyone_mentions: Optional[bool] = None,
    ):
        settings = bot.get_guild_settings(interaction.guild_id)
        changed = False
        if mentions is not None:
            for key in (
                "allow_user_mentions",
                "allow_role_mentions",
                "allow_everyone_mentions",
            ):
                settings[key] = mentions
            changed = True

        mention_updates = {
            "allow_user_mentions": user_mentions,
            "allow_role_mentions": role_mentions,
            "allow_everyone_mentions": everyone_mentions,
        }

        for key, value in mention_updates.items():
            if value is not None:
                settings[key] = value
                changed = True

        if not changed:
            await reply(
                interaction,
                "No settings changed. Provide at least one toggle.",
                ephemeral=True,
            )
            return

        bot.set_guild_settings(interaction.guild_id, settings)
        await reply(interaction, format_settings(settings), ephemeral=True)

    @app_commands.command(name="output", description="Toggle generated output filters")
    @app_commands.describe(
        links="Allow generated messages to include links.",
        emojis="Allow generated messages to include custom or Unicode emojis.",
    )
    @settings_permissions_check()
    @app_commands.guild_only()
    async def output(
        self,
        interaction: discord.Interaction,
        links: Optional[bool] = None,
        emojis: Optional[bool] = None,
    ):
        settings = bot.get_guild_settings(interaction.guild_id)
        updates = {
            "allow_links": links,
            "allow_emojis": emojis,
        }

        changed = False
        for key, value in updates.items():
            if value is not None:
                settings[key] = value
                changed = True

        if not changed:
            await reply(
                interaction,
                "No settings changed. Provide at least one toggle.",
                ephemeral=True,
            )
            return

        bot.set_guild_settings(interaction.guild_id, settings)
        await reply(interaction, format_settings(settings), ephemeral=True)

class PrivacyCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="privacy", description="Manage your bot privacy")

    @app_commands.command(name="status", description="Show whether you are opted out")
    async def status(self, interaction: discord.Interaction):
        if bot.is_user_opted_out(interaction.user.id):
            message = "You are opted out. I will not record your future messages."
        else:
            message = "You are opted in. I may record your messages in enabled channels."
        await reply(interaction, message, ephemeral=True)

    @app_commands.command(name="opt-out", description="Stop the bot from recording your messages")
    async def opt_out(self, interaction: discord.Interaction):
        if bot.is_user_opted_out(interaction.user.id):
            await reply(interaction, "You are already opted out.", ephemeral=True)
            return

        bot.opt_out_user(interaction.user.id)
        bot.data_handler.flush_user(interaction.user.id)
        bot.markov_chains.clear()
        await reply(
            interaction,
            "You are opted out. Your user memory was deleted and future messages will be ignored.",
            ephemeral=True,
        )

    @app_commands.command(name="opt-in", description="Allow the bot to record your messages again")
    async def opt_in(self, interaction: discord.Interaction):
        if not bot.is_user_opted_out(interaction.user.id):
            await reply(interaction, "You are already opted in.", ephemeral=True)
            return

        bot.opt_in_user(interaction.user.id)
        await reply(
            interaction,
            "You are opted in. Future messages in enabled channels may be recorded.",
            ephemeral=True,
        )


@app_commands.command(name="gen", description="Generate a message")
@app_commands.describe(
    user="Mention a user to generate a message based on their data.",
    length="Maximum length in words. Default is 20, max is 100.",
)
@app_commands.guild_only()
async def gen(
    interaction: discord.Interaction,
    user: Optional[discord.User] = None,
    length: int = 20,
):
    await bot.generate_message(interaction, user=user, length=length)


class MarkovBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        os.makedirs(DATA_DIR, exist_ok=True)
        self.tree = app_commands.CommandTree(self)
        self.tree.on_error = self.on_app_command_error
        self.data_handler = DataHandler()
        self.markov_chains = {}
        self.enabled_channels = set()
        self.guild_settings = {}
        self.opted_out_users = set()

        self.tree.add_command(SettingsCommands())
        self.tree.add_command(PrivacyCommands())
        self.tree.add_command(gen)

    async def setup_hook(self):
        await self.tree.sync()
        print("Synced commands to Discord.")

    async def on_ready(self):
        print(f"Logged in as {self.user.name}")  # type: ignore[union-attr]
        self.load_settings()

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await reply(
                interaction,
                "You need Administrator or Manage Server permissions to use this command.",
                ephemeral=True,
            )
            return

        if isinstance(error, app_commands.NoPrivateMessage):
            await reply(
                interaction,
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        traceback.print_exception(type(error), error, error.__traceback__)
        await reply(
            interaction,
            "An unexpected error occurred while running that command.",
            ephemeral=True,
        )

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
        else:
            settings = {
                "enabled_channels": [],
                "guild_settings": {},
                "opted_out_users": [],
            }

        self.enabled_channels.update(settings.get("enabled_channels", []))
        self.guild_settings = {
            str(guild_id): normalize_guild_settings(guild_settings)
            for guild_id, guild_settings in settings.get("guild_settings", {}).items()
        }
        self.opted_out_users = normalize_user_ids(settings.get("opted_out_users", []))
        self.save_settings()

    def save_settings(self):
        write_json_atomic(
            SETTINGS_FILE,
            {
                "enabled_channels": list(self.enabled_channels),
                "guild_settings": self.guild_settings,
                "opted_out_users": sorted(self.opted_out_users),
            },
        )

    def is_user_opted_out(self, user_id: int) -> bool:
        return user_id in self.opted_out_users

    def opt_out_user(self, user_id: int):
        self.opted_out_users.add(user_id)
        self.save_settings()

    def opt_in_user(self, user_id: int):
        self.opted_out_users.discard(user_id)
        self.save_settings()

    def get_guild_settings(self, guild_id: Optional[int]) -> dict[str, Any]:
        if guild_id is None:
            return normalize_guild_settings(None)

        key = str(guild_id)
        if key not in self.guild_settings:
            self.guild_settings[key] = normalize_guild_settings(None)
        return deepcopy(self.guild_settings[key])

    def set_guild_settings(self, guild_id: Optional[int], settings: dict[str, Any]):
        if guild_id is None:
            return

        self.guild_settings[str(guild_id)] = normalize_guild_settings(settings)
        self.save_settings()

    def generate_filtered_message(
        self,
        chain: MarkovChain,
        *,
        max_length: int,
        guild_id: Optional[int],
    ) -> tuple[str, list[str]]:
        settings = self.get_guild_settings(guild_id)
        last_reasons = []

        for _ in range(MAX_GENERATION_RETRIES):
            generated = truncate_for_discord(chain.generate_sentence(max_length=max_length).strip())
            if not generated:
                return "", []

            reasons = filter_reasons(generated, settings)
            if not reasons:
                return generated, []
            last_reasons = reasons

        return "", last_reasons

    async def generate_message(
        self,
        interaction: discord.Interaction,
        *,
        user: Optional[discord.User],
        length: int,
    ):
        if interaction.guild_id is None:
            await reply(
                interaction,
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        max_allowed_length = 100
        if length < 1 or length > max_allowed_length:
            await reply(
                interaction,
                f"Length must be a positive number between 1 and {max_allowed_length}.",
                ephemeral=True,
            )
            return

        if user:
            if self.is_user_opted_out(user.id):
                await reply(
                    interaction,
                    f"{user.name} has opted out of the bot.",
                    ephemeral=True,
                )
                return

            chain_id = user_chain_key(interaction.guild_id, user.id)
            missing_data_message = f"Not enough data to generate a message for {user.name}."
            data = self.data_handler.get_user_data(user.id, guild_id=interaction.guild_id)
        else:
            chain_id = interaction.channel_id
            missing_data_message = "Not enough data to generate a message for this channel."
            data = self.data_handler.get_channel_data(
                interaction.channel_id,
                excluded_user_ids=self.opted_out_users,
            )

        if chain_id not in self.markov_chains:
            if not data:
                await reply(interaction, missing_data_message, ephemeral=True)
                return

            self.markov_chains[chain_id] = MarkovChain()
            self.markov_chains[chain_id].build_model(data)

        generated, reasons = self.generate_filtered_message(
            self.markov_chains[chain_id],
            max_length=length,
            guild_id=interaction.guild_id,
        )
        if not generated:
            if reasons:
                await reply(
                    interaction,
                    f"Generated messages were blocked by the current filters: {', '.join(reasons)}.",
                    ephemeral=True,
                )
                return

            await reply(interaction, missing_data_message, ephemeral=True)
            return

        settings = self.get_guild_settings(interaction.guild_id)
        await reply(
            interaction,
            generated,
            allowed_mentions=allowed_mentions_for(settings),
        )

    async def on_message(self, message: discord.Message):
        if message.author == self.user or message.guild is None:
            return

        if message.channel.id not in self.enabled_channels:
            return

        if self.is_user_opted_out(message.author.id):
            return

        self.data_handler.add_channel_message(
            message.channel.id,
            message.author.id,
            message.content,
            timestamp=message.created_at,
        )
        self.data_handler.add_user_message(
            message.author.id,
            message.channel.id,
            message.content,
            timestamp=message.created_at,
            guild_id=message.guild.id,
        )

        if message.channel.id in self.markov_chains:
            self.markov_chains[message.channel.id].add_text(message.content)
        user_chain_id = user_chain_key(message.guild.id, message.author.id)
        if user_chain_id in self.markov_chains:
            self.markov_chains[user_chain_id].add_text(message.content)


if __name__ == "__main__":
    bot = MarkovBot()
    bot.run(config["token"])
