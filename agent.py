import pandas as pd
from collections import Counter
from managers.discard_manager import DiscardManager

from game import Player, Card
from managers.hints_manager import HintsManager
from managers.play_manager import PlayManager


class Agent(Player):
    def __init__(self, name, index, num_cards, ruleset):
        super().__init__(name)
        self.index = index
        self.ruleset = ruleset
        self.players = []  # list of the other players name ordered by turn (from mine on)
        self.card_hints_manager = HintsManager(self)
        self.card_play_manager = PlayManager(self)
        self.card_discard_manager = DiscardManager(self)
        self.NUM_NUMBERS = 5
        self.NUM_COLORS = 5
        self.COLORS = ["red", "yellow", "green", "white", "blue"]
        self.full_deck = self.get_full_deck()
        self.full_deck_composition = self.counterOfCards(self.full_deck)
        self.possibilities = [self.counterOfCards(self.full_deck) for i in
                              range(num_cards)]  # -> list (one element for each card_pos) of Counters (color,value)
        print("Initialized agent: ", self.name)
        global redf
        redf = open('possibilities/possibilities' + self.name + '.txt', 'w+')
        print("----- INITIALIZE AGENT:", file=redf, flush=True)
        self.print_possibilities()

    def set_players(self, observation):
        for i in range(self.index + 1, len(observation['players'])):
            self.players.append(observation['players'][i].name)
        for i in range(0, self.index):
            self.players.append(observation['players'][i].name)

    # SHUFFLE
    def rl_choice(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        """
        # UPDATE POSSIBILITIES
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                  observation['players'])
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        action = 1
        while action is not None:
            for rule in self.ruleset.active_rules:
                action = self.ruleset.rules[rule](self, observation)
                if action is not None: return action

        print("something wrong")

    # FLOW ALPHA
    def rule_choice(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        """
        # UPDATE POSSIBILITIES
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                  observation['players'])
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        # CHOOSE ACTION
        # 1) Check if there is a playable card (probability 1 of being playable)
        action = self.ruleset.play_best_card_prob(self, observation, 1)
        if action is not None: return action
        # 2) If a lot of hints have been played, try to discard a useless or duplicate card
        if observation['usedNoteTokens'] > 5:
            action = self.ruleset.discard_useless_card(self, observation)
            if action is not None: return action
            action = self.ruleset.discard_duplicate_card(self, observation)
            if action is not None: return action
        # 3) If it is not possible to hint, discard
        if observation['usedNoteTokens'] == 8:
            action = self.safe_discard_sequence(observation)
            if action is not None: return action
        # 4) Try to hint next then other players with an helpful hint
        action = self.ruleset.give_helpful_hint(self, observation)
        if action is not None: return action
        # 6) Discard safely a card
        action = self.safe_discard_sequence(observation)
        if action is not None: return action
        # 7) If no token has been used yet (its not possible to discard)
        if observation['usedNoteTokens'] == 0:
            action = self.hint_sequence(observation)
            if action is not None: return action
        # 8) You still have 3 lives
        if observation['usedStormTokens'] == 0:
            # try to play a card if there is one with at least 60% of probability
            action = self.ruleset.play_best_card_prob(self, observation, 0.6)
            if action is not None: return action

            if observation['usedNoteTokens'] < 4:  # or hint
                action = self.hint_sequence(observation)
                if action is not None: return action
        # 8) You still have 2 lives
        elif observation['usedStormTokens'] == 1:
            action = self.ruleset.play_best_card_prob(self, observation, 0.8)
            if action is not None: return action

        action = self.hint_sequence(observation)
        if action is not None: return action

        action = self.discard_sequence(observation)
        if action is not None: return action

        action = self.ruleset.tell_ones(self, observation)
        if action is not None: return action
        action = self.ruleset.tell_fives(self, observation)
        if action is not None: return action
        action = self.ruleset.tell_unknown(self, observation)
        if action is not None: return action
        action = self.ruleset.tell_randomly(self, observation)
        if action is not None: return action

        action = self.ruleset.play_best_card_prob(self, observation, 0.8)
        if action is not None: return action

        action = self.ruleset.play_oldest(self, observation)
        if action is not None: return action

        print("Something went wrong")

        return None

    # FLOW BETA
    def rule_choice_beta(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        """
        # UPDATE POSSIBILITIES
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                  observation['players'])
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        # CHOOSE ACTION
        # 1) Check if there is a playable card
        action = self.ruleset.play_best_card_prob(self, observation, 1)
        if action is not None: return action
        # 1.b) If there are less than 5 cards in the discard pile, discard the dead cards
        if len(observation['discard_pile']) < 5 and observation['usedNoteTokens'] > 0:
            action = self.ruleset.discard_useless_card(self, observation)
            if action is not None: return action
        # 2) If it is not possible to hint, discard
        if observation['usedNoteTokens'] == 8:
            action = self.safe_discard_sequence(observation)
            if action is not None: return action
        # 3) If you can hint, try first to give an helpful hint to the next player
        else:
            action = self.hint_sequence(observation)
            if action is not None: return action
        # 4) If no token has been used yet
        if observation['usedNoteTokens'] == 0:
            action = self.ruleset.tell_unknown(self, observation)
            if action is not None: return action
            action = self.ruleset.tell_ones(self, observation)
            if action is not None: return action
            action = self.ruleset.tell_fives(self, observation)
            if action is not None: return action
            action = self.ruleset.tell_randomly(self, observation)
            if action is not None: return action
        # 8)
        if observation['usedStormTokens'] < 2:
            action = self.ruleset.play_best_card_prob(self, observation, 0.6)
            if action is not None: return action

            if observation['usedNoteTokens'] < 6:
                action = self.hint_sequence(observation)
                if action is not None: return action
            action = self.discard_sequence(observation)
            if action is not None: return action

        elif observation['usedStormTokens'] == 2:
            action = self.ruleset.play_best_card_prob(self, observation, 0.9)
            if action is not None: return action

        action = self.hint_sequence(observation)
        if action is not None: return action

        action = self.discard_sequence(observation)
        if action is not None: return action
        action = self.ruleset.tell_unknown(self, observation)
        if action is not None: return action
        action = self.ruleset.tell_randomly(self, observation)
        if action is not None: return action
        return None

    # FLOW DELTA
    def rule_choice_delta(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        """
        # UPDATE POSSIBILITIES
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                  observation['players'])
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        # CHOOSE ACTION
        # 1) Check if there is a playable card
        action = self.ruleset.play_best_card_prob(self, observation, 0.86)
        if action is not None: return action
        # 2) If we have token then use them!!! (with two player we can know a lot with 8 hints)
        if observation['usedNoteTokens'] < 8:
            action = self.hint_sequence(observation)
            if action is not None: return action
        # 3) Still at least 2 lives -> try to play a card with at least 60% probability of being playable
        if observation['usedStormTokens'] < 2:
            action = self.ruleset.play_best_card_prob(self, observation, 0.6)
            if action is not None: return action
        # 4) discard
        action = self.discard_sequence(observation)
        if action is not None: return action
        # 5) if nothing better found, discard oldest 
        action = self.ruleset.discard_oldest(self, observation)
        if action is not None: return action
        # 6) if you can not discard and you still have lives, play the card with highest probability of being playable
        # (praying the gods)
        if observation['usedStormTokens'] == 1 and observation['usedNoteTokens'] == 0:
            # will return the card with the highest probability of being playable but with no threshold on the
            # probability
            action = self.ruleset.play_best_card_prob(self, observation, 0.0)
            if action is not None: return action
        else:
            # otherwise better to not risk and just hint to someone something unknown to them
            action = self.ruleset.tell_unknown(self, observation)
            if action is not None: return action

        print("Something wrong happened")
        return None

    def hint_sequence(self, observation):
        action = self.ruleset.give_helpful_hint(self, observation)
        if action is not None: return action
        action = self.ruleset.tell_most_information(self, observation, 3)
        if action is not None: return action
        action = self.ruleset.give_useful_hint(self, observation)
        if action is not None: return action
        return None

    def discard_sequence(self, observation):
        action = self.ruleset.discard_useless_card(self, observation)
        if action is not None: return action
        action = self.ruleset.discard_duplicate_card(self, observation)
        if action is not None: return action
        action = self.ruleset.discard_less_relevant(self, observation)
        if action is not None: return action
        return None

    def safe_discard_sequence(self, observation):
        action = self.ruleset.discard_useless_card(self, observation)
        if action is not None: return action
        action = self.ruleset.discard_duplicate_card(self, observation)
        if action is not None: return action
        return None

    def vanDerBergh_choice(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        It follows the van der bergh strategy:
        https://www.researchgate.net/publication/319853435_Aspects_of_the_Cooperative_Card_Game_Hanabi
        (optimized for 3 players)
        """
        # UPDATE POSSIBILITIES
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                  observation['players'])
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        # CHOOSE ACTION
        # 1) Check if there is a card playable with prob 60%
        action = self.ruleset.play_best_card_prob(self, observation, 0.6)
        if action is not None: return action
        # 2) discard a 100% useless card
        action = self.ruleset.discard_useless_card(self, observation)
        if action is not None: return action
        # 3) hint about a card that is immediately playable
        action = self.ruleset.give_useful_hint(self, observation)
        if action is not None: return action
        # 4) hint about the most informative
        action = self.ruleset.tell_most_information(self, observation)
        if action is not None: return action
        # 5) discard less relevant
        action = self.ruleset.discard_less_relevant(self, observation)
        if action is not None: return action

        print("something went wrong")

    def vanDerBergh_choice_prob(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        It follows the van der bergh strategy:
        https://www.researchgate.net/publication/319853435_Aspects_of_the_Cooperative_Card_Game_Hanabi
        (optimized for 3 players)
        """
        # UPDATE POSSIBILITIES
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                  observation['players'])
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        # CHOOSE ACTION
        # 1) Check if there is a card playable with prob 60%
        if observation['usedStormTokens'] == 0:
            prob = 0.6
        if observation['usedStormTokens'] == 1:
            prob = 0.6
        if observation['usedStormTokens'] == 2:
            prob = 0.9  # better not to risk
        action = self.ruleset.play_best_card_prob(self, observation, prob)
        if action is not None: return action
        # 2) discard a 100% useless card
        action = self.ruleset.discard_useless_card(self, observation)
        if action is not None: return action
        # 3) hint about a card that is immediately playable
        action = self.ruleset.give_useful_hint(self, observation)
        if action is not None: return action
        # 4) hint about the most informative
        action = self.ruleset.tell_most_information(self, observation)
        if action is not None: return action
        # 5) discard less relevant
        action = self.ruleset.discard_less_relevant(self, observation)
        if action is not None: return action

        print("something went wrong")

    def piers_choice(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        It follows the piers strategy as explained here: https://www.researchgate.net/publication/318294875_Evaluating_and_modelling_Hanabi-playing_agents
        """
        # UPDATE POSSIBILITIES
        # Start by updating the possibilities (should take hints into account?)
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                  observation['players'])
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        # CHOOSE ACTION
        # 1) IfRule (lives > 1 ∧ ¬deck.hasCardsLeft) Then (PlayProbablySafeCard(0.0))
        lives = 3 - observation['usedStormTokens']
        visible_cards = self.visible_cards(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                           observation['players'])
        deck_left_cards = self.full_deck_composition - visible_cards
        number_cards_left = sum(deck_left_cards.values())
        if (lives > 1 and number_cards_left <= 0):
            action = self.ruleset.play_best_card_prob(self, observation, 0.0)
            if action is not None: return action
        # 2) PlaySafeCard
        action = self.ruleset.play_best_card_prob(self, observation, 1.0)
        if action is not None: return action
        # 3) IfRule (lives > 1) Then (PlayProbablySafeCard(0.6))
        if (lives > 1):
            action = self.ruleset.play_best_card_prob(self, observation, 0.6)
            if action is not None: return action
        # 4) TellAnyoneAboutUsefulCard
        action = self.ruleset.give_useful_hint(self, observation)
        if action is not None: return action
        # 5) IfRule (information < 4) Then (TellDispensable)
        information = 8 - observation['usedNoteTokens']
        if (information < 4):
            action = self.ruleset.tell_useless(self, observation)
            if action is not None: return action
        # 6) discard useless
        action = self.ruleset.discard_useless_card(self, observation)
        if action is not None: return action
        # 7) DiscardOldestFirst
        action = self.ruleset.discard_oldest(self, observation)
        if action is not None: return action
        # 8) Tell randomly
        action = self.ruleset.tell_randomly(self, observation)
        if action is not None: return action
        # 9) Discard less relevant
        action = self.ruleset.discard_less_relevant(self, observation)
        if action is not None: return action

        print("something went wrong")

    def osawa_outer_choice(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        It follows the osawa outer strategy
         (optimized for 2 players)
        """
        # UPDATE POSSIBILITIES
        # Start by updating the possibilities (should take hints into account?)
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']),
                                  observation['players'])
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        # CHOOSE ACTION
        # 1) Check if there is a card playable with prob 100%
        action = self.ruleset.play_best_card_prob(self, observation, 1.0)
        if action is not None: return action
        # 2) discard a 100% useless card
        action = self.ruleset.discard_useless_card(self, observation)
        if action is not None: return action
        # 3) hint about a card that is immediately playable
        action = self.ruleset.give_useful_hint(self, observation)
        if action is not None: return action
        # 4) hint about the most informative
        action = self.ruleset.tell_unknown(self, observation)
        if action is not None: return action
        # 5) discard less relevant
        action = self.ruleset.discard_less_relevant(self, observation)
        if action is not None: return action

        print("something went wrong")

    def receive_hint(self, destination, hint_type, value, positions):
        """
        The agent received an hint from outside
        @param destination: the player to which the hint is destined
        @param hint_type: the type of hint (value or color)
        @param value: the value of the hint (number or color depending on the type)
        @param positions: the positions of the card in the hand associated with the hint
        """
        self.card_hints_manager.received_hint(destination, hint_type, value, positions)

    def update_possibilities(self, board, discard_pile, players):
        """
        Update the possibilities by removing visible cards
        @param board: cards that are currently on the table
        @param discard_pile: cards that are currently on the discard pile
        """
        visible_cards = self.visible_cards(board, discard_pile, players)
        for p in self.possibilities:
            for card in self.full_deck_composition:
                if card in p:
                    p[card] = self.full_deck_composition[card] - visible_cards[card]
                    assert p[card] >= 0
                    if p[card] == 0:
                        del p[card]

    def visible_cards(self, board, discard_pile, players):
        """
        Counter of all the cards visible by me
        @param board: cards that are currently on the table
        @param discard_pile: cards that are currently on the discard pile
        """
        res = discard_pile
        for player_info in players:
            res += self.counterOfCards(player_info.hand)
        for color, cards in board.items():
            res += self.counterOfCards(cards)
        return res

    def reset_possibilities(self, card_pos, new_card=True):
        """
        Resets the possibilities when a card is moved out of the hand
        @param card_pos: index of the card that has been moved out in the hand
        @param new_card: new card that will replace the gone one
        """
        self.possibilities.pop(card_pos)
        if new_card:
            self.possibilities.append(self.counterOfCards(self.full_deck))

    def print_possibilities(self, playersKnowledge=None):
        """
        Displays possibilities
        @param playersKnowledge: knowledge of the players about their cards
        """
        for (card_pos, p) in enumerate(self.possibilities):
            table = {"red": [0] * 5, "green": [0] * 5, "blue": [0] * 5, "white": [0] * 5, "yellow": [0] * 5}
            table = pd.DataFrame(table, index=[1, 2, 3, 4, 5])
            for card in p:
                table.loc[card[1], card[0]] = p[card]
            print("Card pos:" + str(card_pos), file=redf, flush=True)
            print(table, file=redf, flush=True)
            if playersKnowledge is not None:
                print("knowledge:" + str(playersKnowledge[self.name][card_pos]), file=redf, flush=True)
            print("--------------------------------------", file=redf, flush=True)

    def relevant_card(self, card, board, full_deck, discard_pile):
        """
        Is this card the last copy available of a playable card?
        @param card: card for which the relevance is questioned
        @param board: cards that are currently on the table
        @param full_deck: counter of the whole set of cards
        @param discard_pile: counter of the cards within the discard pile
        @return:
        """
        color = card[0]
        value = card[1]
        copies_in_deck = full_deck[(color, value)]  # total of cards of (color, value)  for example 3
        copies_in_discard_pile = discard_pile[(color, value)]  # total of this type of cards discarded 2
        return self.useful_card(card, board, full_deck, discard_pile) and copies_in_deck == copies_in_discard_pile + 1

    @staticmethod
    def useful_card(card, board, full_deck, discard_pile):
        """
        Is this card still useful?
        @param card: card for which the relevance is questioned tuple (color,value)
        @param board: cards that are currently on the table
        @param full_deck: counter of the whole set of cards
        @param discard_pile: counter of the cards within the discard pile
        """
        color = card[0]
        value = card[1]
        last_value_in_board = len(board[color])
        for number in range(last_value_in_board + 1,
                            value):  # consider the cards that need to be played before the specific card
            copies_in_deck = full_deck[(color, number)]  # tot copies
            copies_in_discard_pile = discard_pile[(color, number)]  # copies discarded
            if copies_in_deck == copies_in_discard_pile:  # the card is in someone players or still in the deck
                return False
        return value > last_value_in_board

    @staticmethod
    def playable_card(card, board):
        """
        Is this card playable on the board?
        @param card: card for which the playability is checked
        @param board: cards that are currently on the table
        """
        if isinstance(card, Card):
            return card.value == len(board[card.color]) + 1
        elif isinstance(card, tuple):
            color = card[0]
            value = card[1]
            if len(board[color]) == 0:
                if value == 1:
                    return True
            elif value == len(board[color]) + 1:
                return True

            return False
        else:
            assert (False)  # something went wrong

    @staticmethod
    def get_full_deck():
        """
        Returns a generic copy of the full_deck
        """
        cards = []
        numCards = 0
        for _ in range(3):
            cards.append(Card(numCards, 1, "red"))
            numCards += 1
            cards.append(Card(numCards, 1, "yellow"))
            numCards += 1
            cards.append(Card(numCards, 1, "green"))
            numCards += 1
            cards.append(Card(numCards, 1, "blue"))
            numCards += 1
            cards.append(Card(numCards, 1, "white"))
            numCards += 1
        for _ in range(2):
            cards.append(Card(numCards, 2, "red"))
            numCards += 1
            cards.append(Card(numCards, 2, "yellow"))
            numCards += 1
            cards.append(Card(numCards, 2, "green"))
            numCards += 1
            cards.append(Card(numCards, 2, "blue"))
            numCards += 1
            cards.append(Card(numCards, 2, "white"))
            numCards += 1
        for _ in range(2):
            cards.append(Card(numCards, 3, "red"))
            numCards += 1
            cards.append(Card(numCards, 3, "yellow"))
            numCards += 1
            cards.append(Card(numCards, 3, "green"))
            numCards += 1
            cards.append(Card(numCards, 3, "blue"))
            numCards += 1
            cards.append(Card(numCards, 3, "white"))
            numCards += 1
        for _ in range(2):
            cards.append(Card(numCards, 4, "red"))
            numCards += 1
            cards.append(Card(numCards, 4, "yellow"))
            numCards += 1
            cards.append(Card(numCards, 4, "green"))
            numCards += 1
            cards.append(Card(numCards, 4, "blue"))
            numCards += 1
            cards.append(Card(numCards, 4, "white"))
            numCards += 1
        for _ in range(1):
            cards.append(Card(numCards, 5, "red"))
            numCards += 1
            cards.append(Card(numCards, 5, "yellow"))
            numCards += 1
            cards.append(Card(numCards, 5, "green"))
            numCards += 1
            cards.append(Card(numCards, 5, "blue"))
            numCards += 1
            cards.append(Card(numCards, 5, "white"))
            numCards += 1
        return cards

    @staticmethod
    def counterOfCards(cardList=[]):
        """
        Gets as input a list of Card.
        Output = Counter with keys (color,value)
        """
        counterCard = {}
        for card in cardList:
            key = (card.color, card.value)
            if key not in counterCard:
                counterCard[key] = 1
            else:
                counterCard[key] += 1
        return Counter(counterCard)


class Knowledge:
    """
    An instance of this class represents what a player knows about a card, as known by everyone.
    """

    def __init__(self, color=None, value=None):
        self.color = color
        self.value = value

    def knows(self, hint_type):
        """
        Does the player know the color/number?
        """
        if hint_type == "color":
            return self.color is not None
        else:
            return self.value is not None

    def __repr__(self):
        return ("C: " + str(self.color) if self.color is not None else "-") + (
            "V:" + str(self.value) if self.value is not None else "-")
