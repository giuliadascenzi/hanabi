#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import sys
import itertools
import copy
import GameData

class DiscardManager(object):
    """
    Discard Manager.
    """
    def __init__(self, agent):
        self.agent = agent    # my agent object

    def get_best_discard(self, observation):
        """
        Choose the best card to be discarded.
        """
        # first see if I can be sure to discard a useless card
        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p = Counter of (color, value) tuples with the number of occurrences
            # representing the possible (color,value) for a card in pos card_pos
            # one for each card
            if len(p) > 0 and all(
                    not self.useful_card(card, observation['fireworks'], self.agent.full_deck_composition,
                                            self.agent.counterOfCards(observation['discard_pile'])) for card in p):
                print("considering to discard useless card")
                return card_pos, 0.0, 0.0

        # Try to avoid cards that are (on average) more relevant, then choose cards that are (on average) less useful
        tolerance = 1e-3
        best_cards_pos = []

        WEIGHT = {number: self.NUM_NUMBERS + 1 - number for number in range(1, self.NUM_NUMBERS + 1)}
        best_relevant_weight = max(WEIGHT.values())
        relevant_weight = None

        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p = Counter of (color, value) tuples with the number of occurrences representing the possible
            # (color,value) for a card in pos card_pos, one for each card
            if len(p) > 0:
                relevant_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if
                                            self.agent.relevant_card(card, observation['fireworks'], self.agent.full_deck_composition,
                                                                self.agent.counterOfCards(observation['discard_pile'])))

                relevant_weight = float(relevant_weight_sum) / sum(p.values())

                useful_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if
                                        self.agent.useful_card(card, observation['fireworks'], self.agent.full_deck_composition,
                                                            self.agent.counterOfCards(observation['discard_pile'])))
                useful_weight = float(useful_weight_sum) / sum(p.values())

                if relevant_weight < best_relevant_weight - tolerance:
                    # better weight found
                    best_cards_pos, best_relevant_weight, = [], relevant_weight

                if relevant_weight < best_relevant_weight + tolerance:
                    # add this card to the possibilities
                    best_cards_pos.append((useful_weight, card_pos))

        assert len(best_cards_pos) > 0
        print("Best card pos: ", best_cards_pos)
        useful_weight, card_pos = min(best_cards_pos, key=lambda t: t[0])  # consider the one with minor useful_weight

        print("considering to discard a card (pos %d, relevant weight ~%.3f, useful weight %.3f)"
                % (card_pos, best_relevant_weight, useful_weight))
        return card_pos, relevant_weight, useful_weight