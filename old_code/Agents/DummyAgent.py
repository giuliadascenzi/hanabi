from Agents.BaseAgent import BaseAgent
import random
from game import Player, Card
import GameData
from collections import Counter


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

        if self.usedNoteTokens < 8 and random.randint(0,2) == 0:
            # give random hint to the next player
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
            
            print(">>>give some random hint")
            return GameData.ClientHintData(self.name, destination_name, type, value)
        
        elif random.randint(0,1) == 0 or self.usedNoteTokens == 0 :
            # play random card
            card_pos = random.choice([0,1,2,3,4])
            print(">>>play some random card")
            return GameData.ClientPlayerPlayCardRequest(self.name, card_pos)
        
        else:
            # discard random card
            card_pos = random.choice([0,1,2,3,4])
            print(">>>discard some random card")
            return GameData.ClientPlayerDiscardCardRequest(self.name, card_pos)

    