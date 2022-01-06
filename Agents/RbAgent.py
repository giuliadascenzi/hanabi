from Agents.BaseAgent import BaseAgent
import random
from game import Player, Card
import GameData
from collections import Counter


def get_full_deck():
    """
    returns a generic copy of the full_deck
    """
    cards = []
    numCards=0
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


class Knowledge:
    """
    An instance of this class represents what a player knows about a card, as known by everyone.
    """
    
    def __init__(self, color=False, number=False):
        self.color = color                  # know the color
        self.number = number                # know the number
        self.playable = False               # at some point, this card was playable
        self.non_playable = False           # at some point, this card was not playable
        self.useless = False                # this card is useless
        self.high = False                   # at some point, this card was high (see CardHintsManager)
    
    
    def __repr__(self):
        return ("C" if self.color else "-") + ("N" if self.number else "-") + ("P" if self.playable else "-") + ("Q" if self.non_playable else "-") + ("L" if self.useless else "-") + ("H" if self.high else "-")
    
    
    def knows(self, hint_type):
        """
        Does the player know the color/number?
        """
        assert hint_type in Action.HINT_TYPES
        if hint_type == Action.COLOR:
            return self.color
        else:
            return self.number
    
    def knows_exactly(self):
        """
        Does the player know exactly this card?
        """
        return self.color and (self.number or self.playable)




class DummyAgent(BaseAgent):
    """
    An instance of this class represents a player's strategy.
    It only has the knowledge of that player, and it must make decisions.

    It performs only random choices
    """
    
    def __init__(self, name):
        super().__init__(name)
    
    def initialize(self, num_players, players_names, k, board, players_info, discard_pile):
        """
        To be called once before the beginning.
        """

        self.num_players = num_players
        self.players_names = players_names
        self.k = k  # number of cards per hand
        self.usedNoteTokens = 0
        self.usedStormTokens= 0

        self.board = board
        self.players_info = players_info
        self.discard_pile = discard_pile

        # store a copy of the full deck
        self.full_deck = get_full_deck()
        self.deck_size = len(self.full_deck)
        self.full_deck_composition = Counter(self.full_deck)

        # for each of my card, store its possibilities
        self.possibilities = [Counter(self.full_deck) for i in range(self.k)]
        
        # remove cards of other players from possibilities
        #self.update_possibilities()
        
        # knowledge of all players
        self.knowledge = [[Knowledge(color=False, number=False) for j in range(k)] for i in range(num_players)]

    def update(self, board, players_info, discardPile, usedNoteTokens, usedStormTokens, turn= 0, last_turn=0 ):
        """
        To be called immediately after every turn.
        """
        self.usedNoteTokens = usedNoteTokens
        self.usedStormTokens = usedStormTokens
        self.turn = turn
        self.last_turn = last_turn

        self.players_info = players_info
        self.discard_pile = discardPile
        self.board= board
             
    def get_turn_action(self):
        """
        Choose action for this turn.
        Returns the request to the server
        """
        # update possibilities checking all combinations if deck is small 

        if self.usedNoteTokens < 8 and random.randint(0,2) == 0:
            # give random hint to the next player
            destination_name, value, type = self.get_best_hint()
            
            print(">>>give some random hint")
            return GameData.ClientHintData(self.name, destination_name, type, value)
        
        elif random.randint(0,1) == 0 or self.usedNoteTokens == 0 :
            # play random card
            card_pos = self.get_best_play()
            print(">>>play some random card")
            return GameData.ClientPlayerPlayCardRequest(self.name, card_pos)
        
        else:
            # discard random card
            card_pos = self.get_best_discard()
            print(">>>discard some random card")
            return GameData.ClientPlayerDiscardCardRequest(self.name, card_pos)

    def get_best_play(self):
        return random.choice([0,1,2,3,4])

    def get_best_discard(self):
        return random.choice([0,1,2,3,4])

    def get_best_hint(self):
        next_player_index = (self.players_names.index(self.name)+1) % self.num_players
        destination_name = self.players_names[next_player_index]
        destination_hand = ""
        for player_info in self.players_info:
            if player_info.name== destination_name:
                destination_hand= player_info.hand
        card = random.choice([card for card in destination_hand if card is not None])

        if random.randint(0,1) == 0:
            type= "color"
            value = card.color
        else:
            type=  "value"
            value = card.value
        return destination_name, value, type
