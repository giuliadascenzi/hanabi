import random
import copy
import pandas as pd
from collections import Counter

from game import Player, Card
import GameData
from hints_manager import HintsManager


class Agent(Player):
    def __init__(self, name, players, index, num_cards):
        super().__init__(name)
        print("Agent initialized: ", name )
        self.players_names = players
        self.players = None
        self.index = index
        self.num_cards = num_cards
        self.full_deck = self.get_full_deck()
        self.possibilities = [self.counterOfCards(self.full_deck) for i in range(self.num_cards)]
        self.full_deck_composition = self.counterOfCards(self.full_deck)
        self.NUM_NUMBERS = 5
        self.NUM_COLORS = 5
        self.COLORS = ["red", "yellow", "green", "white", "blue"]
        self.card_hints_manager = HintsManager(self)

        global redf
        redf = open('possibilities/possibilities' + self.name + '.txt', 'w')
        print("----- INITIALIZE AGENT:", file=redf, flush=True)
        self.print_possibilities()

    def rl_choice(self, observation):
        """
        Choose action for this turn.
        Returns the request to the server
        """
        self.players = observation['players']
        # Start by updating the possibilities (should take hints into account?)
        self.update_possibilities(observation['fireworks'], self.counterOfCards(observation['discard_pile']))

        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities(observation['playersKnowledge'])

        # 1) Check if there is a playable card
        card_pos = self.get_best_play(observation)
        if card_pos is not None:
            print(">>>play the card number:", card_pos)
            return GameData.ClientPlayerPlayCardRequest(self.name, card_pos)

        # 2) If a usefull hint can be done do it:
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = self.get_best_hint(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the helpful hint ", type, " ", value, " to ", destination_name)
                ''''  TODO: Not helpful here since receive_hint is just for hint received by the agent not sent
                positions = []
                for player in self.players:
                    if player.name == destination_name:
                        for card in player.hand:
                            if card.value == value or card.color == value:
                                positions.append(player.hand.index(card))
                self.card_hints_manager.receive_hint(destination_name, type, value, positions)
                '''
                return GameData.ClientHintData(self.name, destination_name, type, value)

        # 3) If I can not discard, give a random hint
        if observation['usedNoteTokens'] == 0:
            destination_name, value, type = self.get_low_value_hint(observation)
            print(">>>give the low_value hint ", type, " ", value, " to ", destination_name)
            return GameData.ClientHintData(self.name, destination_name, type, value)

        # 4) If it is not possible to hint
        if observation['usedNoteTokens'] == 8:
            card_pos, _, _ = self.get_best_discard(observation)
            print(">>>discard the card number:", card_pos)
            return GameData.ClientPlayerDiscardCardRequest(self.name, card_pos)

        # Else: randomly choose between discard or give a random
        elif random.randint(0, 1) == 0:
            # discard
            card_pos, _, _ = self.get_best_discard(observation)
            print(">>>discard the card number:", card_pos)
            return GameData.ClientPlayerDiscardCardRequest(self.name, card_pos)

        else:
            destination_name, value, type = self.get_low_value_hint(observation)
            print(">>>give the low_value hint ", type, " ", value, " to ", destination_name)
            return GameData.ClientHintData(self.name, destination_name, type, value)
    
    def receive_hint(self, destination, type, value, positions):
        '''
        the agent received an hint from outside
        '''
        self.card_hints_manager.receive_hint(destination, type, value, positions)

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
    def counterOfCards(cardList):
        """
        Gets as input a list of Card.
        Output = Counter with keys (color,value)
        """
        counterCard = {}
        for card in cardList:
            # key of the dictionary tuple of (color, value)
            key = (card.color, card.value)
            if key not in counterCard:
                counterCard[key] = 1
            else:
                counterCard[key] += 1
        return Counter(counterCard)

    def update_possibilities(self, board, discard_pile):
        """
        Update possibilities removing visible cards.
        """
        visible_cards = self.visible_cards(board, discard_pile)
        for p in self.possibilities:
            for card in self.full_deck_composition:
                if card in p:
                    # this card is still possible, update the number of possible occurrences
                    p[card] = self.full_deck_composition[card] - visible_cards[card]

                    if p[card] == 0:
                        # remove this card
                        del p[card]


    def print_possibilities(self, playersKnowledge= None):
        for (card_pos, p) in enumerate(self.possibilities):
            table = {"red": [0] * 5, "green": [0] * 5, "blue": [0] * 5,
                     "white": [0] * 5, "yellow": [0] * 5}
            table = pd.DataFrame(table, index=[1, 2, 3, 4, 5])
            for card in p:
                table.loc[card[1], card[0]] = p[card]

            print("Card pos:" + str(card_pos), file=redf, flush=True)
            print(table, file=redf, flush=True)
            if (playersKnowledge!=None):
                print("knowledge:" + str(playersKnowledge[self.name][card_pos] ), file=redf, flush=True)
            print("--------------------------------------", file=redf, flush=True)

    def get_best_play(self, observation):
        WEIGHT = {number: self.NUM_NUMBERS - number for number in range(1, self.NUM_NUMBERS)}
        WEIGHT[self.NUM_NUMBERS] = self.NUM_NUMBERS

        tolerance = 1e-3
        best_card_pos = None
        best_avg_num_playable = -1.0  # average number of other playable cards, after my play
        best_avg_weight = 0.0  # average weight (in the sense above)
        for (card_pos, p) in enumerate(self.possibilities):
            # p = Counter of possible tuple (card,value)
            if all(self.is_playable(card, observation['fireworks']) for card in p) and len(p) > 0:
                # the card in this position is surely playable!
                # how many cards of the other players become playable, on average?
                num_playable = []
                for card in p:
                    # Remember that p is a tuple (color, value)
                    color = card[0]
                    value = card[1]
                    fake_board = copy.copy(observation['fireworks'])
                    fake_board[color].append(value)
                    for i in range(p[card]):
                        num_playable.append(sum(1 for player_info in self.players for c in player_info.hand if
                                                c is not None and self.playable_card(c, fake_board)))

                avg_num_playable = float(sum(num_playable)) / len(num_playable)

                avg_weight = float(sum(WEIGHT[card[1]] * p[card] for card in p)) / sum(p.values())
                if avg_num_playable > best_avg_num_playable + tolerance or \
                        avg_num_playable > best_avg_num_playable - tolerance and avg_weight > best_avg_weight:
                    print("update card to be played, pos %d, score %f, %f" % (card_pos, avg_num_playable, avg_weight))
                    best_card_pos, best_avg_num_playable, best_avg_weight = card_pos, avg_num_playable, avg_weight

        if best_card_pos is not None:
            print("playing card in position %d gives %f playable cards on average and weight %f" % (
                best_card_pos, best_avg_num_playable, best_avg_weight))
            return best_card_pos
        # elif random.randint(0,3) == 0:
        #    return random.randint(0,4)
        else:
            return best_card_pos

    # Not used but put here in case we want to use it anyway
    def maybe_play_lowest_playable_card(self, observation):
        """
        The Bot checks if previously a card has been hinted to him,
        :param observation:
        :return:
        """
        own_card_knowledge = []
        for p in observation['playersKnowledge']:
            if p['player'] == self.name:
                own_card_knowledge = p['knowledge']

        for k in own_card_knowledge:
            if k.color is not None:
                return GameData.ClientPlayerPlayCardRequest(self.name, own_card_knowledge.index(k))

        for k in own_card_knowledge:
            if k.value is not None:
                return GameData.ClientPlayerPlayCardRequest(self.name, own_card_knowledge.index(k))

    def get_best_discard(self, observation):
        """
        Choose the best card to be discarded.
        """
        # first see if I can be sure to discard a useless card
        for (card_pos, p) in enumerate(self.possibilities):
            # p = Counter of (color, value) tuples with the number of occurrences
            # representing the possible (color,value) for a card in pos card_pos
            # one for each card
            if len(p) > 0 and all(
                    not self.useful_card(card, observation['fireworks'], self.full_deck_composition,
                                         self.counterOfCards(observation['discard_pile'])) for card in p):
                print("considering to discard useless card")
                return card_pos, 0.0, 0.0

        # Try to avoid cards that are (on average) more relevant, then choose cards that are (on average) less useful
        tolerance = 1e-3
        best_cards_pos = []

        WEIGHT = {number: self.NUM_NUMBERS + 1 - number for number in range(1, self.NUM_NUMBERS + 1)}
        best_relevant_weight = max(WEIGHT.values())
        relevant_weight = None

        for (card_pos, p) in enumerate(self.possibilities):
            # p = Counter of (color, value) tuples with the number of occurrences representing the possible
            # (color,value) for a card in pos card_pos, one for each card
            if len(p) > 0:
                relevant_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if
                                          self.relevant_card(card, observation['fireworks'], self.full_deck_composition,
                                                             self.counterOfCards(observation['discard_pile'])))

                relevant_weight = float(relevant_weight_sum) / sum(p.values())

                useful_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if
                                        self.useful_card(card, observation['fireworks'], self.full_deck_composition,
                                                         self.counterOfCards(observation['discard_pile'])))
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

    def get_best_hint(self, observation):
        return self.card_hints_manager.get_hint(observation)

    def get_low_value_hint(self, observation):
        return self.card_hints_manager.get_low_value_hint(observation)


    ########################
    #    Card functions    #
    ########################

    def visible_cards(self, board, discard_pile):
        """
        Counter of all the cards visible by me.
        """
        # consider the discard_pile
        res = discard_pile
        # consider the cards of the team mates
        for player_info in self.players:
            res += self.counterOfCards(player_info.hand)
        # consider the cards already played
        for color, cards in board.items():
            res += self.counterOfCards(cards)
        return res

    @staticmethod
    def is_playable(card, board):
        """
        card = tuple (color, value)
        """
        color = card[0]
        value = card[1]
        if len(board[color]) == 0:
            if value == 1:
                return True
        elif value == len(board[color]) + 1:
            return True

        return False

    @staticmethod
    def playable_card(card, board):
        """
        Is this card playable on the board?
        """
        return card.value == len(board[card.color]) + 1

    @staticmethod
    def useful_card(card, board, full_deck, discard_pile):
        """
        Is this card still useful?
        full_deck and discard_pile are Counters.
        REMEMBER: card is a tuple (color, value)
        """
        # check that lower cards still exist
        color = card[0]
        value = card[1]

        last_value_in_board = len(board[color])

        for number in range(last_value_in_board + 1, value):
            copies_in_deck = full_deck[(color, number)]
            copies_in_discard_pile = discard_pile[(color, number)]

            if copies_in_deck == copies_in_discard_pile:
                # some lower card was discarded!
                return False

        return value > last_value_in_board

    def relevant_card(self, card, board, full_deck, discard_pile):
        """
        Is this card the last copy available?
        full_deck and discard_pile are Counters.
        """
        color = card[0]
        value = card[1]
        copies_in_deck = full_deck[(color, value)]
        copies_in_discard_pile = discard_pile[(color, value)]
        return self.useful_card(card, board, full_deck, discard_pile) and copies_in_deck == copies_in_discard_pile + 1

    @staticmethod
    def card_matches(card1, card2):
        if card1[0] is not None and card1[0] != card2[0]:
            return False
        if card1[1] is not None and card1[1] != card2[1]:
            return False
        else:
            return True

    def reset_possibilities(self, card_pos, new_card=True):
        # Remove the card played/discarded
        self.possibilities.pop(card_pos)
        if new_card:  # if there are still cards to draw in the deck
            # Append a new Counter of possibilities object for the new card (with the default value)
            self.possibilities.append(self.counterOfCards(self.full_deck))
        return

    def dummy_agent_choice(self, observation):
        if observation['usedNoteTokens'] < 3 and random.randint(0, 2) == 0:
            # give random hint to the next player
            next_player_index = (observation['players'].index(self.name) + 1) % len(observation['players'])
            destination = observation['players'][next_player_index]
            card = random.choice([card for card in observation['playerHands'][next_player_index].hand
                                  if card is not None])
            if random.randint(0, 1) == 0:
                type_ = "color"
                value = card.color
            else:
                type_ = "value"
                value = card.value
            print("Give some random hint")
            return GameData.ClientHintData(self.name, destination, type_, value)

        elif random.randint(0, 1) == 0:
            # play random card
            card_pos = random.choice([0, 1, 2, 3, 4])
            print("Play some random card")
            return GameData.ClientPlayerPlayCardRequest(self.name, card_pos)

        else:
            # discard random card
            card_pos = random.choice([0, 1, 2, 3, 4])
            print("Discard some random card")
            return GameData.ClientPlayerDiscardCardRequest(self.name, card_pos)

    def simple_heuristic_choice(self, observation):
        # Check if there are any pending hints and play the card corresponding to the hint.
        for d in observation['hints']:
            if d['player'] == self.name:
                return GameData.ClientPlayerPlayCardRequest(self.name, d['card_index'])

        # Check if it's possible to hint a card to your colleagues.
        fireworks = observation['fireworks']
        if observation['usedNoteTokens'] < 8:
            # Check if there are any playable cards in the hands of the opponents.
            for player in observation['players']:
                player_hand = player.hand
                player_hints = []
                for d in observation['hints']:
                    if d['player'] == player.name:
                        player_hints.append(d)
                # Check if the card in the hand of the opponent is playable.
                # Try first to complete an hint
                for card, hint in zip(player_hand, player_hints):
                    if self.playable_card(card, fireworks) and (hint['color'] is None):
                        return GameData.ClientHintData(self.name, player.name, 'color', card.color)
                    elif self.playable_card(card, fireworks) and (hint['value'] is None):
                        return GameData.ClientHintData(self.name, player.name, 'value', card.value)
                # If not possible, give the value
                for card in player_hand:
                    if self.playable_card(card, fireworks):
                        return GameData.ClientHintData(self.name, player.name, 'value', card.value)

        # If not then discard or play card number 0
        if observation['usedNoteTokens'] > 1:
            return GameData.ClientPlayerDiscardCardRequest(self.name, 0)
        else:
            return GameData.ClientPlayerPlayCardRequest(self.name, 0)


class Knowledge:
    """
    An instance of this class represents what a player knows about a card, as known by everyone.
    """

    def __init__(self, color=False, value=False):
        self.color = color  # know the color
        self.value = value  # know the number
        self.playable = False  # at some point, this card was playable
        self.non_playable = False  # at some point, this card was not playable
        self.useless = False  # this card is useless
        self.high = False  # at some point, this card was high (relevant/discardable)(see CardHintsManager)

    def __repr__(self):
        return ("C: "+ str(self.color) if self.color else "-") + ("V:"+ str(self.value) if self.value else "-") + (
            "P" if self.playable else "-") + ("Q" if self.non_playable else "-") + ("L" if self.useless else "-") + ("H" if self.high else "-")
    
    def knows(self, hint_type):
        """
        Does the player know the color/number?
        """
        if hint_type == "color":
            return self.color
        else:
            return self.value

    def knows_exactly(self):
        """
        Does the player know exactly this card?
        """
        return self.color and (self.value or self.playable)