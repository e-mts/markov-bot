# markov_chain.py

import random

class MarkovChain:
    def __init__(self, order=2):
        self.order = order  # The order of the Markov chain
        self.model = {}  # The Markov model

    def build_model(self, data):
        for line in data:
            self.add_text(line)

    def add_text(self, text):
        words = text.split()
        for i in range(len(words) - self.order):
            key = tuple(words[i:i+self.order])
            next_word = words[i+self.order]
            if key not in self.model:
                self.model[key] = []
            self.model[key].append(next_word)

    def generate_sentence(self, max_length=20):
        if not self.model:
            return ""

        # Start with a random key
        key = random.choice(list(self.model.keys()))
        generated = list(key)

        for _ in range(max_length - self.order):
            next_words = self.model.get(key)
            if not next_words:
                break
            next_word = random.choice(next_words)
            generated.append(next_word)
            key = tuple(generated[-self.order:])
        
        return ' '.join(generated)