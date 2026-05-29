import random
import re
from collections import Counter, defaultdict


END_TOKEN = "<__END__>"
UNICODE_EMOJI_TOKEN_PATTERN = (
    "[\U0001F1E6-\U0001F1FF]{2}"
    "|[\U0001F300-\U0001FAFF\u2600-\u27BF]\ufe0f?"
    "(?:\u200d[\U0001F300-\U0001FAFF\u2600-\u27BF]\ufe0f?)*"
)
TOKEN_PATTERN = re.compile(
    r"<a?:[A-Za-z0-9_]+:\d+>"
    f"|{UNICODE_EMOJI_TOKEN_PATTERN}"
    r"|https?://\S+"
    r"|www\.\S+"
    r"|<@!?\d+>"
    r"|<@&\d+>"
    r"|<#\d+>"
    r"|@everyone"
    r"|@here"
    r"|\.{2,}"
    r"|[\w']+"
    r"|[^\s]",
    re.UNICODE,
)
SENTENCE_END_TOKENS = {".", "!", "?", "..."}
NO_SPACE_BEFORE = {
    ".",
    ",",
    "!",
    "?",
    ":",
    ";",
    "%",
    ")",
    "]",
    "}",
}
NO_SPACE_AFTER = {"(", "[", "{", "$"}


def tokenize(text):
    return TOKEN_PATTERN.findall(text)


def sentence_tokenize(text):
    sentences = []
    current = []

    for token in tokenize(text):
        current.append(token)
        if token in SENTENCE_END_TOKENS:
            sentences.append(current)
            current = []

    if current:
        sentences.append(current)

    return sentences


def detokenize(tokens):
    message = ""
    for token in tokens:
        if not message:
            message = token
        elif token in NO_SPACE_BEFORE:
            message += token
        elif message[-1] in NO_SPACE_AFTER:
            message += token
        else:
            message += f" {token}"
    return message


class MarkovChain:
    def __init__(self, order=2, replay_window=8, rng=None):
        if order < 1:
            raise ValueError("order must be at least 1")

        self.order = order
        self.replay_window = replay_window
        self.random = rng or random
        self.models = {
            context_order: defaultdict(Counter)
            for context_order in range(1, order + 1)
        }
        self.starts = {
            context_order: Counter()
            for context_order in range(1, order + 1)
        }
        self.source_messages = set()
        self.source_windows = set()
        self.model = self.models[order]

    def build_model(self, data):
        for line in data:
            self.add_text(line)

    def add_text(self, text):
        for sentence in sentence_tokenize(text):
            self.add_sentence(sentence)

    def add_sentence(self, tokens):
        if not tokens:
            return

        self._remember_source(tokens)

        max_context_order = min(self.order, len(tokens))
        for context_order in range(1, max_context_order + 1):
            self.starts[context_order][tuple(tokens[:context_order])] += 1

        tokens_with_end = tokens + [END_TOKEN]
        for context_order in range(1, max_context_order + 1):
            for index in range(len(tokens_with_end) - context_order):
                key = tuple(tokens_with_end[index:index + context_order])
                next_token = tokens_with_end[index + context_order]
                self.models[context_order][key][next_token] += 1

    def generate_sentence(self, max_length=20, avoid_replay=True, max_attempts=10):
        if max_length < 1:
            return ""
        if not self._has_model():
            return ""

        fallback_tokens = []
        for _ in range(max_attempts):
            tokens = self._generate_tokens(max_length)
            if not tokens:
                return ""

            fallback_tokens = tokens
            if not avoid_replay or not self._looks_like_replay(tokens):
                return detokenize(tokens)

        return detokenize(fallback_tokens)

    def _has_model(self):
        return any(self.starts[context_order] for context_order in self.starts)

    def _generate_tokens(self, max_length):
        start = self._choose_start()
        if not start:
            return []

        generated = list(start[:max_length])
        while len(generated) < max_length:
            next_token = self._choose_next(generated)
            if not next_token or next_token == END_TOKEN:
                break
            generated.append(next_token)

        return generated

    def _choose_start(self):
        available_orders = [
            context_order
            for context_order, starts in self.starts.items()
            if starts
        ]
        if not available_orders:
            return ()

        context_order = min(self.order, max(available_orders))
        return self._weighted_choice(self.starts[context_order])

    def _choose_next(self, context):
        for context_order in range(min(self.order, len(context)), 0, -1):
            key = tuple(context[-context_order:])
            choices = self.models[context_order].get(key)
            if choices:
                return self._weighted_choice(choices)
        return END_TOKEN

    def _weighted_choice(self, counter):
        choices = list(counter.keys())
        weights = list(counter.values())
        return self.random.choices(choices, weights=weights, k=1)[0]

    def _remember_source(self, tokens):
        normalized = self._normalize_tokens(tokens)
        self.source_messages.add(normalized)

        if len(normalized) < self.replay_window:
            return

        for index in range(len(normalized) - self.replay_window + 1):
            self.source_windows.add(
                normalized[index:index + self.replay_window]
            )

    def _looks_like_replay(self, tokens):
        normalized = self._normalize_tokens(tokens)
        if normalized in self.source_messages:
            return True
        if len(normalized) < self.replay_window:
            return False

        for index in range(len(normalized) - self.replay_window + 1):
            if normalized[index:index + self.replay_window] in self.source_windows:
                return True
        return False

    def _normalize_tokens(self, tokens):
        return tuple(token.lower() for token in tokens)
