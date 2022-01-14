from Agents.BaseAgent import BaseAgent
import random
from game import Player, Card
import GameData
from collections import Counter
import copy
from .hints_manager import HintsManager

redf = ""


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
    
    def __init__(self, color=False, value=False):
        self.color = color                  # know the color
        self.value = value                  # know the number
        self.playable = False               # at some point, this card was playable
        self.non_playable = False           # at some point, this card was not playable
        self.useless = False                # this card is useless
        self.high = False                   # at some point, this card was high (relevant/discardable)(see CardHintsManager)
    
    
    def __repr__(self):
        return ("C" if self.color else "-") + ("N" if self.value else "-") + ("P" if self.playable else "-") + ("Q" if self.non_playable else "-") + ("L" if self.useless else "-") + ("H" if self.high else "-")
    
    
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



class RbAgent(BaseAgent):
    """
    An instance of this class represents a player's strategy.
    It only has the knowledge of that player, and it must make decisions.

    """
    
    def __init__(self, name):
        super().__init__(name)
    
    def initialize(self, num_players, players_names, k, board, players_info, discard_pile):
        """
        To be called once before the beginning.
        """
        global redf
        redf = open('possibilities' + self.name + '.txt', 'w')
        print("Initializing agent: ", self.name)
        self.turn = 0
        self.NUM_NUMBERS = 5
        self.NUM_COLORS = 5
        self.COLORS = ["red", "yellow", "green", "white", "blue"]

        self.num_players = num_players
        self.players_names = players_names 
        self.k = k  # number of cards per hand
        self.usedNoteTokens = 0
        self.usedStormTokens= 0

        self.board = board
        self.players_info = players_info
        self.discard_pile = self.counterOfCards(discard_pile)

        self.my_hand = [0 for i in range(self.k)] # hand of the player (does not know the cards, so all set to 0 or to None if there is no a card anymore at that position).
                                                     

        # store a copy of the full deck
        self.full_deck = get_full_deck()
        self.deck_size = len(self.full_deck)
        self.full_deck_composition = self.counterOfCards(self.full_deck)
        
        # knowledge of all players  "player_name" : [list of Knowledge objects (one for each card, sorted by card_pos) ]       
        self.knowledge = {name: [Knowledge(color=False, value=False) for j in range(self.k)] for name in self.players_names }

        # for each of my card, store its possibilities
        self.possibilities = [self.counterOfCards(self.full_deck) for i in range(self.k)]
        print("----- INITIALIZE AGENT:", file=redf, flush=True)
        self.print_possibilities()
        # remove cards of other players from possibilities
        self.update_possibilities()

        self.card_hints_manager = HintsManager(self)


    def counterOfCards(self, cardList):
        """
        It gets as imput a list of Card.
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
           

    def update(self, board, players_info, discardPile, usedNoteTokens, usedStormTokens, turn= 0, last_turn=0 ):
        """
        To be called immediately after every turn.
        """
        self.usedNoteTokens = usedNoteTokens
        self.usedStormTokens = usedStormTokens
        self.turn = turn
        self.last_turn = last_turn

        self.players_info = players_info
        self.discard_pile = self.counterOfCards(discardPile)
        self.board= board
        self.update_possibilities()
             
    def update_possibilities(self):
        """
        Update possibilities removing visible cards.
        """
        visible_cards = self.visible_cards()
        for p in self.possibilities:
            for card in self.full_deck_composition:
                if card in p:
                    # this card is still possible
                    # update the number of possible occurrences
                    p[card] = self.full_deck_composition[card] - visible_cards[card]
                    
                    if p[card] == 0:
                        # remove this card
                        del p[card]
        
        print("----- UPDATED POSSIBILITIES:", file=redf, flush=True)
        self.print_possibilities()
        
    
    def get_turn_action(self):
        """
        Choose action for this turn.
        Returns the request to the server
        """
        # update possibilities checking all combinations if deck is small 

        # 1) Check if there is a playable card

        card_pos = self.get_best_play()

        if (card_pos is not None):
            print(">>>play the card number:", card_pos)
            return GameData.ClientPlayerPlayCardRequest(self.name, card_pos)
        
        # 2) If a usefull hint can be done do it:
        if (self.usedNoteTokens < 8 ):
            destination_name, value, type = self.get_best_hint()
            if (destination_name, value, type) != (None, None, None): # found a best hint
                print(">>>give the helpful hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(self.name, destination_name, type, value)
        # 3) If I can not discard, give a random hint
        if (self.usedNoteTokens == 0):
            destination_name, value, type = self.get_low_value_hint()
            print(">>>give the low_value hint ", type, " ", value, " to ", destination_name)
            return GameData.ClientHintData(self.name, destination_name, type, value)
        # 4) If it is not possible to hint
        if (self.usedNoteTokens == 8): 
            card_pos,_,_ = self.get_best_discard()
            print(">>>discard the card number:", card_pos)
            return GameData.ClientPlayerDiscardCardRequest(self.name, card_pos)

        # Else: randomly choose between discard or give a random
        elif (random.randint(0,1) == 0) : 
            # discard 
            card_pos,_,_ = self.get_best_discard()
            print(">>>discard the card number:", card_pos)
            return GameData.ClientPlayerDiscardCardRequest(self.name, card_pos)
         
        
        else:
            destination_name, value, type = self.get_low_value_hint()
            print(">>>give the low_valuehint ", type, " ", value, " to ", destination_name)
            return GameData.ClientHintData(self.name, destination_name, type, value)
        

            

    def feed_turn(self, playerName, data):
        """
        Receive information about a played turn. (either of the same player)
        data is the object coming from the server
        """

        if type(data) is not GameData.ServerHintData:      #PLAY or DISCARD if data.type is none 
            # A card has been removed (played or discarded), we need to remove the information about it + add  new default ones for the new card (if exists)
            cardHandIndex = data.cardHandIndex
            
            # 1) Remove it from the knowledge list 
            self.reset_knowledge(playerName, cardHandIndex, self.k == data.handLength)
            
            if playerName == self.name:
                # 2) If the player is me, remove the possibilities belonging to the discarded/played card + add a new default one for the new card (if exists)
                self.reset_possibilities(cardHandIndex, self.k == data.handLength)
                '''
                # 3) if the card played/discarded was mine and there are no cards left in the deck -> set to null the card_pos of my hand that do not corrispond to cards anymore 
                if (self.k != data.handLength):
                    self.hand[data.handLength] = None
                '''
               
        else:
            # someone gave a hint!
            # the suitable hints manager must process it
            self.card_hints_manager.receive_hint(data)
        
        self.turn = self.turn+1
        # update possibilities with visible cards
        #self.update_possibilities()
        
        pass

    def print_possibilities(self):
        import pandas as pd
        for (card_pos, p) in enumerate(self.possibilities):
            table = {"red": [0]*5 , "green": [0]*5, "blue": [0]*5, "white": [0]*5, "yellow": [0]*5  }
            table = pd.DataFrame(table, index= [1,2,3,4,5])
            for card in p:
                table.loc[card[1],card[0]] = p[card]

            print("Card pos:" + str(card_pos), file=redf, flush=True)
            print(table, file=redf, flush=True)
            self.print_knowledge(self.name, card_pos)
            print("--------------------------------------", file=redf, flush=True)

    def print_knowledge(self, player, card_pos):
        print("knowledge:" + str(self.knowledge[player][card_pos] ), file=redf, flush=True)
        return
        


    def get_best_play(self):
        WEIGHT = {number: self.NUM_NUMBERS - number for number in range(1,  self.NUM_NUMBERS)}
        WEIGHT[ self.NUM_NUMBERS] =  self.NUM_NUMBERS
        
        tolerance = 1e-3
        best_card_pos = None
        best_avg_num_playable = -1.0    # average number of other playable cards, after my play
        best_avg_weight = 0.0           # average weight (in the sense above)
        for (card_pos, p) in enumerate(self.possibilities):
            # p = Counter of possible tuple (card,value)            
            if all( self.is_playable(card) for card in p) and len(p) > 0:
                # the card in this position is surely playable!
                # how many cards of the other players become playable, on average?
                num_playable = []
                for card in p:
                    # Remember that p is a tuple (color, value)
                    color = card[0]
                    value = card[1]
                    fake_board = copy.copy(self.board)
                    fake_board[color].append(value)
                    for i in range(p[card]):
                        num_playable.append(sum(1 for player_info in self.players_info for c in player_info.hand if c is not None and self.playable_card(c, fake_board)))
                
                avg_num_playable = float(sum(num_playable)) / len(num_playable)
                
                avg_weight = float(sum(WEIGHT[card[1]] * p[card] for card in p)) / sum(p.values())
                if avg_num_playable > best_avg_num_playable + tolerance or avg_num_playable > best_avg_num_playable - tolerance and avg_weight > best_avg_weight:
                    print("update card to be played, pos %d, score %f, %f" % (card_pos, avg_num_playable, avg_weight))
                    best_card_pos, best_avg_num_playable, best_avg_weight = card_pos, avg_num_playable, avg_weight

        if best_card_pos is not None:
            print("playing card in position %d gives %f playable cards on average and weight %f" % (best_card_pos, best_avg_num_playable, best_avg_weight))
            return best_card_pos

        else:
            return best_card_pos

    def get_best_discard(self):
        """
        Choose the best card to be discarded.
        """
        # first see if I can be sure to discard a useless card
        for (card_pos, p) in enumerate(self.possibilities):
            # p = Counter of (color, value) tuples with the number of occurrencies
            # representing the possible (color,value) for a card in pos card_pos
            # one for each card
            if len(p) > 0 and all(not self.useful_card(card, self.board, self.full_deck_composition, self.discard_pile) for card in p):
                print("considering to discard useless card")
                return card_pos, 0.0, 0.0
        
        # Try to avoid cards that are (on average) more relevant, then choose cards that are (on average) less useful
        tolerance = 1e-3
        best_cards_pos = []
        best_relevant_ratio = 1.0
        
        WEIGHT = {number: self.NUM_NUMBERS + 1 - number for number in range(1, self.NUM_NUMBERS + 1)}
        best_relevant_weight = max(WEIGHT.values())
        
        for (card_pos, p) in enumerate(self.possibilities):
            # p = Counter of (color, value) tuples with the number of occurrencies
            # representing the possible (color,value) for a card in pos card_pos
            # one for each card
            if len(p) > 0:
                num_relevant = sum(p[card] for card in p if self.relevant_card(card, self.board, self.full_deck_composition, self.discard_pile))
                relevant_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if self.relevant_card(card, self.board, self.full_deck_composition, self.discard_pile))
                
                relevant_ratio = float(num_relevant) / sum(p.values())
                relevant_weight = float(relevant_weight_sum) / sum(p.values())
                
                num_useful = sum(p[card] for card in p if self.useful_card(card, self.board, self.full_deck_composition, self.discard_pile))
                useful_weight_sum = sum(WEIGHT[card[1]] * p[card] for card in p if self.useful_card(card, self.board, self.full_deck_composition, self.discard_pile))
                useful_ratio = float(num_useful) / sum(p.values())
                useful_weight = float(useful_weight_sum) / sum(p.values())
                
                
                if relevant_weight < best_relevant_weight - tolerance:
                    # better weight found
                    best_cards_pos, best_relevant_weight, = [], relevant_weight
                
                if relevant_weight < best_relevant_weight + tolerance:
                    # add this card to the possibilities
                    best_cards_pos.append((useful_weight, card_pos))
        
        assert len(best_cards_pos) > 0
        print("Best card pos: ", best_cards_pos)
        useful_weight, card_pos = min(best_cards_pos, key= lambda t: t[0]) #consider the one with minor useful_weight
        
        print("considering to discard a card (pos %d, relevant weight ~%.3f, useful weight %.3f)" % (card_pos, best_relevant_weight, useful_weight))
        return card_pos, relevant_weight, useful_weight

    def get_best_hint(self):

        # try to give hint
        destination_name, value, type = self.card_hints_manager.get_hint()

        return destination_name, value, type

    def get_low_value_hint(self):

        # try to give hint
        destination_name, value, type = self.card_hints_manager.get_low_value_hint()

        return destination_name, value, type

    ########################
    ### ---> Card functions
    ########################

    def visible_cards(self):
        """
        Counter of all the cards visible by me.
        """
        # consider the discard_pile
        res = self.discard_pile
        # consider the cards of the team mates
        for player_info in self.players_info: 
            res += self.counterOfCards(player_info.hand)
        # consider the cards already played
        for color, cards in self.board.items():
            res += self.counterOfCards(cards)
        return res

    def is_playable(self, card):
        """
        card = tuple (color, value)
        """
        color = card[0]
        value = card[1]
        if len(self.board[color]) == 0:
            if value == 1:
                return True
        elif value == len(self.board[color]) + 1:
            return True
        
        return False

    def playable_card(self, card, board):
        """
        Is this card playable on the board?
        """
        return card.value == len(board[card.color]) + 1

    def useful_card(self, card, board, full_deck, discard_pile):
        """
        Is this card still useful?
        full_deck and discard_pile are Counters.
        REMEMBER: card is a tuple (color, value)
        """
        # check that lower cards still exist
        color = card[0]
        value = card[1]

        last_value_in_board = len( board[color] )

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

    def card_matches(self, card1, card2):
        if (card1[0]!=None and card1[0] != card2[0]):
            return False
        if (card1[1]!=None and card1[1] != card2[1]):
            return False
        else: return True

    def reset_knowledge(self, playername, card_pos, new_card = True):
        # Remove the card played/discarded
        self.knowledge[playername].pop(card_pos) 
        if (new_card): # if there are still cards to draw in the deck
            # Append a new knowledge object for the new card
            self.knowledge[playername].append( Knowledge(False, False) ) 
        return     

    def reset_possibilities(self, card_pos, new_card = True):
        # Remove the card played/discarded
        self.possibilities.pop(card_pos) 
        if (new_card): # if there are still cards to draw in the deck
            # Append a new Counter of possibilities object for the new card (with the default value)
            self.possibilities.append( self.counterOfCards(self.full_deck) ) 
        return     



