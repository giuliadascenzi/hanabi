#!/usr/bin/env python
# -*- coding: utf-8 -*-


import random


class DiscardManager(object):
    """
    Discard Manager.
    """

    def __init__(self, agent):
        self.agent = agent  # my agent object

    def discard_useless_card(self, observation, lowest=False):
        """
        Discards a card surely useless
        @param observation: state of the game
        @return: useless card to be discarded
        """
        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p = Counter of (color, value) tuples with the number of occurrences
            # representing the possible (color,value) for a card in pos card_pos
            # one for each card
            useless = []
            if len(p) > 0 and all(
                    not self.agent.useful_card(card, observation['fireworks'], self.agent.full_deck_composition,
                                               self.agent.counterOfCards(observation['discard_pile'])) for card in p):
                if lowest:
                    useless.append([card_pos, p.value])
                # whatever card is this is useless
                else:
                    return card_pos
            if lowest:
                useless.sort(key=lambda x: x[1])
                return useless[0][0]
        return None

    def discard_less_relevant(self, observation):
        """
        discard a less relevant card
        """
        # Try to avoid cards that are (on average) more relevant, then choose cards that are (on average) less useful
        tolerance = 1e-3
        best_cards_pos = []

        WEIGHT = {number: self.agent.NUM_NUMBERS + 1 - number for number in range(1, self.agent.NUM_NUMBERS + 1)}
        best_relevant_weight = max(WEIGHT.values())
        relevant_weight = None

        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p = Counter of (color, value) tuples with the number of occurrences representing the possible
            # (color,value) for a card in pos card_pos, one for each card
            if len(p) > 0:
                relevant_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if
                                          self.agent.relevant_card(card, observation['fireworks'],
                                                                   self.agent.full_deck_composition,
                                                                   self.agent.counterOfCards(
                                                                       observation['discard_pile'])))

                relevant_weight = float(relevant_weight_sum) / sum(p.values())

                useful_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if
                                        self.agent.useful_card(card, observation['fireworks'],
                                                               self.agent.full_deck_composition,
                                                               self.agent.counterOfCards(observation['discard_pile'])))
                useful_weight = float(useful_weight_sum) / sum(p.values())

                if relevant_weight < best_relevant_weight - tolerance:
                    # better weight found
                    best_cards_pos, best_relevant_weight, = [], relevant_weight

                if relevant_weight < best_relevant_weight + tolerance:
                    # add this card to the possibilities
                    best_cards_pos.append((useful_weight, card_pos))

        assert len(best_cards_pos) > 0
        useful_weight, card_pos = min(best_cards_pos, key=lambda t: t[0])  # consider the one with minor useful_weight

        # print("considering to discard a card (pos %d, relevant weight ~%.3f, useful weight %.3f)"
        #        % (card_pos, best_relevant_weight, useful_weight))
        return card_pos

    def discard_duplicate_card(self, observation):
        """
        Discard a card that I see in some other player's hand
        """
        if observation['usedNoteTokens'] != 0:
            cards_in_player_hands = self.agent.counterOfCards()
            for player_info in observation['players']:
                if player_info.name != self.agent.name:
                    cards_in_player_hands += self.agent.counterOfCards(player_info.hand)

            for (card_pos, p) in enumerate(self.agent.possibilities):
                # for each possible value of the card I check that Its already in someone hand
                if all(cards_in_player_hands[c] != 0 for c in p):
                    # this card is surely a duplicate
                    return card_pos
            else:
                return None
        return None

    def discard_oldest_first(self, observation):
        """
        Discards the card that has been held in the hand the longest amount of time
        """
        card_pos = 0
        return card_pos
    
    def discard_randomly(self, observation):
        """
        Discards the card that has been held in the hand the longest amount of time
        """
        card_pos = random.randint(0, len(self.agent.possibilities)-1)
        return card_pos

    
