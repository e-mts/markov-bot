import importlib.util
import os
import unittest
from pathlib import Path


os.environ.setdefault("DISCORD_TOKEN", "test-token")

MODULE_PATH = Path(__file__).resolve().parents[1] / "__main__.py"
SPEC = importlib.util.spec_from_file_location("bot_main", MODULE_PATH)
bot_main = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bot_main)


class SettingsTests(unittest.TestCase):
    def test_default_settings_allow_generated_output(self):
        settings = bot_main.normalize_guild_settings(None)

        self.assertTrue(settings["allow_user_mentions"])
        self.assertTrue(settings["allow_role_mentions"])
        self.assertTrue(settings["allow_everyone_mentions"])
        self.assertTrue(settings["allow_links"])
        self.assertTrue(settings["allow_emojis"])
        self.assertEqual(settings["banned_words"], [])

    def test_legacy_mentions_setting_expands_to_granular_settings(self):
        settings = bot_main.normalize_guild_settings({"allow_mentions": False})

        self.assertFalse(settings["allow_user_mentions"])
        self.assertFalse(settings["allow_role_mentions"])
        self.assertFalse(settings["allow_everyone_mentions"])

    def test_granular_mentions_override_legacy_setting(self):
        settings = bot_main.normalize_guild_settings(
            {
                "allow_mentions": True,
                "allow_user_mentions": False,
            }
        )

        self.assertFalse(settings["allow_user_mentions"])
        self.assertTrue(settings["allow_role_mentions"])
        self.assertTrue(settings["allow_everyone_mentions"])

    def test_filter_reasons_separates_ping_types(self):
        settings = bot_main.normalize_guild_settings(
            {
                "allow_user_mentions": False,
                "allow_role_mentions": False,
                "allow_everyone_mentions": False,
            }
        )

        self.assertEqual(
            bot_main.filter_reasons("<@123> <@&456> @everyone", settings),
            ["user mentions", "role mentions", "@here/@everyone"],
        )

    def test_allowed_mentions_uses_granular_ping_settings(self):
        settings = bot_main.normalize_guild_settings(
            {
                "allow_user_mentions": True,
                "allow_role_mentions": False,
                "allow_everyone_mentions": True,
            }
        )

        allowed_mentions = bot_main.allowed_mentions_for(settings)

        self.assertTrue(allowed_mentions.users)
        self.assertFalse(allowed_mentions.roles)
        self.assertTrue(allowed_mentions.everyone)
        self.assertFalse(allowed_mentions.replied_user)

    def test_settings_commands_split_pings_from_output(self):
        client = bot_main.MarkovBot()
        settings_command = next(
            command
            for command in client.tree.get_commands()
            if command.name == "settings"
        )

        self.assertEqual(
            [command.name for command in settings_command.commands],
            ["show", "pings", "output", "enable", "disable", "flush", "word-filter"],
        )
        self.assertEqual(
            settings_command.to_dict(client.tree)["default_member_permissions"],
            bot_main.discord.Permissions(administrator=True).value,
        )

        pings_command = next(
            command
            for command in settings_command.commands
            if command.name == "pings"
        )
        output_command = next(
            command
            for command in settings_command.commands
            if command.name == "output"
        )

        self.assertEqual(
            [option["name"] for option in pings_command.to_dict(client.tree)["options"]],
            ["mentions", "users", "roles", "everyone"],
        )
        self.assertEqual(
            [option["name"] for option in output_command.to_dict(client.tree)["options"]],
            ["links", "emojis"],
        )


if __name__ == "__main__":
    unittest.main()
