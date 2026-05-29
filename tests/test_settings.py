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
    def test_legacy_mentions_setting_expands_to_granular_settings(self):
        settings = bot_main.normalize_guild_settings({"allow_mentions": True})

        self.assertTrue(settings["allow_user_mentions"])
        self.assertTrue(settings["allow_role_mentions"])
        self.assertTrue(settings["allow_everyone_mentions"])

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
        settings = bot_main.normalize_guild_settings(None)

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


if __name__ == "__main__":
    unittest.main()
