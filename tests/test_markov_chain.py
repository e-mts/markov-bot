import random
import unittest

from markov_chain import MarkovChain, tokenize


class MarkovChainTests(unittest.TestCase):
    def test_short_messages_are_modeled(self):
        chain = MarkovChain(order=2, rng=random.Random(1))
        chain.build_model(["yes", "no"])

        self.assertIn(chain.generate_sentence(max_length=1), {"yes", "no"})

    def test_max_length_is_respected(self):
        chain = MarkovChain(order=2, rng=random.Random(1))
        chain.build_model(["one two three four"])

        generated = chain.generate_sentence(max_length=1)

        self.assertEqual(len(generated.split()), 1)

    def test_generation_starts_at_sentence_start(self):
        chain = MarkovChain(order=2, rng=random.Random(1))
        chain.build_model(["alpha beta gamma. delta epsilon zeta."])

        generated = chain.generate_sentence(max_length=2, avoid_replay=False)

        self.assertIn(generated, {"alpha beta", "delta epsilon"})

    def test_custom_emoji_is_preserved_as_one_token(self):
        self.assertEqual(tokenize("hi <:wave:123>!"), ["hi", "<:wave:123>", "!"])

    def test_unicode_emoji_sequence_is_preserved_as_one_token(self):
        coder_emoji = "\U0001F468\u200d\U0001F4BB"

        self.assertEqual(tokenize(f"hi {coder_emoji}!"), ["hi", coder_emoji, "!"])


if __name__ == "__main__":
    unittest.main()
