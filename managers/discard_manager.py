class DiscardManager(object):
    """
    Discard Manager.
    """

    def __init__(self, agent):
        self.agent = agent

    def discard_useless_card(self, observation):
        """
        Look for a card surely useless
        @param observation: current state of the game
        @return: the index of the useless card to be discarded or None if there isn't
        """
        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p is a Counter of (color, value) tuples representing the chance that the card is (color, value)
            if len(p) > 0 and all( # if any possible instance of the card is usless then the card is surely useless
                    not self.agent.useful_card(card, observation['fireworks'], self.agent.full_deck_composition,
                                               self.agent.counterOfCards(observation['discard_pile'])) 
                                               for card in p):
                    return card_pos
        return None

    def discard_less_relevant(self, observation):
        """
        Look for the less relevant card by trying to avoid cards that are (on average) more relevant and choosing among
        cards that are (on average) less useful
        @param observation: current state of the game
        @return: the index of the less relevant card in the hand
        """
        tolerance = 1e-3
        best_cards_pos = []
        # HOW TO DECIDE?
        # Look for the card that has the lowest possibility of being relevant (useful+last_copy).
        # In case of tie consider the one that has the lowest useful weight 
        # Weights (value 1 : weight 5) (value 2: weight 4) (value 3: weight 3) (value 4: weight 2) (value 5: weight 1)
        WEIGHT = {number: self.agent.NUM_NUMBERS + 1 - number for number in range(1, self.agent.NUM_NUMBERS + 1)}
        best_relevant_weight = max(WEIGHT.values()) #5 
        # WEIGHT -> If you have both a 1 and a 5 that are the last copy available is better to choose to discard the 5

        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p is a Counter of (color, value) tuples representing the chance that the card is (color, value)
            if len(p) > 0:
                # CHECK IF IT COULD BE RELEVANT (if its the last copy available of a useful card)
                # for each possible (color,value) that the card can have consider the WEIGHT[value] * #tot possibilities that the card can have the value if that (color,value) 
                relevant_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if
                                          self.agent.relevant_card(card, observation['fireworks'],
                                                                   self.agent.full_deck_composition,
                                                                   self.agent.counterOfCards(
                                                                       observation['discard_pile'])))
                
                relevant_weight = float(relevant_weight_sum) / sum(p.values())
                # CHECK IF IT COULD BE USEFUL 
                # for each possible (color,value) that the card can have consider the WEIGHT[value] * #tot possibilities that the card can have the value if that (color,value) 
                useful_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if
                                        self.agent.useful_card(card, observation['fireworks'],
                                                               self.agent.full_deck_composition,
                                                               self.agent.counterOfCards(observation['discard_pile'])))
                useful_weight = float(useful_weight_sum) / sum(p.values())

                if relevant_weight < best_relevant_weight - tolerance:
                    best_cards_pos, best_relevant_weight, = [], relevant_weight # a minor relevant weight has been found

                if relevant_weight < best_relevant_weight + tolerance:
                    best_cards_pos.append((useful_weight, card_pos)) # save card_pos at the given relevant_weight, to then pick the one with lower useful_weight

        assert len(best_cards_pos) > 0
        useful_weight, card_pos = min(best_cards_pos, key=lambda t: t[0])  # consider the one with minor useful_weight

        return card_pos

    def discard_duplicate_card(self, observation):
        """
        Look for a card that I see in some other player's hand
        @param observation: current state of the game
        @return: the index of the duplicate card to be or None if there isn't
        """
        cards_in_player_hands = self.agent.counterOfCards()
        for player_info in observation['players']:
            if player_info.name != self.agent.name:
                cards_in_player_hands += self.agent.counterOfCards(player_info.hand)

        for (card_pos, p) in enumerate(self.agent.possibilities):
            if all(cards_in_player_hands[card] != 0 for card in p):
                # this card is surely a duplicate
                return card_pos
        else:
            return None

    @staticmethod
    def discard_oldest(self, observation=None):
        """
        Look for the card that has been held in the hand the longest amount of time
        @return: the index of the oldest card (i.e. 0)
        """
        return 0
