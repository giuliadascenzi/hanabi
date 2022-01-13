#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import itertools
import copy
import GameData

class BaseHintsManager(object):
    """
    Base class for a HintsManager.
    """
    def __init__(self, strategy):
        self.strategy = strategy    # my strategy object
        
        # copy something from the strategy
        self.name = strategy.name
        self.num_players = strategy.num_players
        self.players_names= strategy.players_names
        self.k = strategy.k
        self.possibilities = strategy.possibilities
        self.full_deck_composition = strategy.full_deck_composition
        self.board = strategy.board
        self.knowledge = strategy.knowledge
        
        self.COLORS_TO_NUMBERS = {color: i for (i, color) in enumerate(self.strategy.COLORS)}
    
    
    def log(self, message):
        self.strategy.log(message)
    
    
    def is_duplicate(self, card):
        """
        Says if the given card is owned by some player who knows everything about it.
        """
        # check other players' hands
        for (player_id, hand) in self.strategy.hands.iteritems():
            for card_pos in range(self.k):
                kn = self.knowledge[player_id][card_pos]
                if kn.knows_exactly() and hand[card_pos] is not None and hand[card_pos].equals(card):
                    return True
        
        # check my hand
        for card_pos in range(self.k):
            kn = self.knowledge[self.id][card_pos]
            if kn.knows_exactly() and any(card.equals(c) for c in self.strategy.possibilities[card_pos]):
                return True
        
        return False
    
    
    def is_usable(self, hinter_id):
        """
        Check that it is possible to pass all the information.
        """
        return True
    
    
    def receive_hint(self, info_action):
        """
        Receive hint ***given by*** player_id and update knowledge. ****given to?!?****
        info_action is an object returned by the server after each hint
        """
        if info_action.destination == self.name:
            # process direct hint
             for (i, p) in enumerate(self.possibilities):
                for card in self.strategy.full_deck_composition:
                    if not self.card_matches_hint(card, info_action, i) and card in p:
                        # self.log("removing card %r from position %d due to hint" % (card, i))
                        del p[card]
        
        # update knowledge
        for card_pos in info_action.positions:
            kn = self.knowledge[info_action.destination][card_pos]
            if info_action.type == "color":
                kn.color = True
            else:
                kn.value = True
        
        assert self.possibilities is self.strategy.possibilities
        assert self.board is self.strategy.board
        assert self.knowledge is self.strategy.knowledge
    
    def card_matches(self, card, type, value):
        # does this card match the given color/number? (if the value is None, it is considered to match) 
        if type == "color" and card[0] != value:
            return False
        elif type == "value" and card[1] != value:
            return False
        return True
    
    def card_matches_hint(self, card, action, card_pos):
        # does this card (in the given position) match the given hint?
        assert type(action) is GameData.ServerHintData
        matches = self.card_matches(card, action.type, action.value)
        hinted_card = (card_pos in action.positions and matches) # card in a hinted position with a possible value that matches the hint
        not_hinted_card = (card_pos not in action.positions and not matches) 
        return hinted_card or not_hinted_card
        
    
    def get_hint(self):
        """
        Compute hint to give.
        """
        raise NotImplementedError
    

class SumBasedHintsManager(BaseHintsManager):
    """
    A HintManager which is based on the following idea.
    Associate an integer (between 0 and M) to any possible hand. Send the sum of the integers
    associated to the hands of the other players, modulo M. Then each other player can decode
    its integer by difference, seeing the hands of the other players.
    
    With this implementation, M = number of cards of the other players. The integer is encoded
    in the choice of the card to give a hint about.
    """
    
    def hash(self, hand, player_id, hinter_id):
        """
        The hash of the hand that we want to communicate.
        Must be an integer.
        """
        # To be overloaded by child classes.
        raise NotImplementedError
    
    
    def hash_range(self, hinter_id):
        """
        Return H such that 0 <= hash < H.
        """
        # To be overloaded by child classes.
        raise NotImplementedError
    
    
    def process_hash(self, x, hinter_id):
        """
        Process the given hash of my hand, passed through a hint.
        Optionally, return data to be used by update_knowledge.
        """
        # To be overloaded by child classes.
        raise NotImplementedError
    
    
    def update_knowledge(self, hinter_id, data=None):
        """
        Update knowledge after a hint has been given.
        Optionally, get data from process_hash.
        """
        # To be overloaded by child classes.
        raise NotImplementedError
    
    
    
    def is_usable(self, hinter_id):
        """
        Check if there are enough cards to pass all the information.
        """
        return self.hash_range(hinter_id) <= self.modulo(hinter_id)
    
    
    def compute_hash_sum(self, hinter_name):
        """
        Compute the sum of the hashes of the hands of the other players, excluding the hinter and myself.
        """
        res = 0
        for player_info in self.strategy.players_info:
            player_name = player_info.name
            if player_name != hinter_name and player_name!=self.name:
                hand =player_info.hand 
                h = self.hash(hand, player_name, hinter_name)
                assert 0 <= h < self.modulo(hinter_name)
                res += h
        return res
    
    
    def cards_to_hints(self, player_id):
        """
        For the given player (different from me) return a matching between each card and the hint (type and value)
        to give in order to recognise that card.
        
        Example 1: 4 White, 4 Yellow, 3 Yellow, 2 Red.
            4 White -> White (color)
            4 Yellow -> 4 (number)
            3 Yellow -> 3 (number)
            2 Red -> Red (color)
        
        Example 2: 4 White, 4 White, 4 Yellow, 3 Yellow.
            4 White -> White (color)
            4 White -> None (both 4 and White would mean other cards)
            4 Yellow -> Yellow (color)
            3 Yellow -> 3 (number)
        
        In case a value is not unique in the hand, color means leftmost card and number means rightmost card.
        """
        # TODO: prefer hints on more than one card (in this way, more information is passed)
        
        assert player_id != self.id
        hand = self.strategy.hands[player_id]
        
        matching = {}
        
        # analyze hints on color
        for color in self.strategy.COLORS:
            cards_pos = [card_pos for (card_pos, card) in enumerate(hand) if card is not None and card.matches(color=color)]
            if len(cards_pos) > 0:
                # pick the leftmost
                card_pos = min(cards_pos)
                matching[card_pos] = ("color", color)
                matching[("color", color)] = card_pos
        
        # analyze hints on numbers
        for number in range(1, self.strategy.NUM_NUMBERS+1):
            cards_pos = [card_pos for (card_pos, card) in enumerate(hand) if card is not None and card.matches(number=number)]
            if len(cards_pos) > 0:
                # pick the rightmost
                card_pos = max(cards_pos)
                matching[card_pos] = ("value", number)
                matching[("value", number)] = card_pos
        
        return matching
    
    
    def hint_to_card(self, info_action):
        """
        From the hint, understand the important card.
        This is the inverse of cards_to_hints.
        """
        if info_action.type == "color":
            # pick the leftmost card
            return min(info_action.positions)
        else:
            # pick the rightmost card
            return max(info_action.positions)
        
    
    def relevant_cards(self, hinterName):
        """
        Matching between integers and cards of players other than the hinter, in the form (player_name, card_pos).
        For example:
            0: (0, 1)   # player 0, card 1
            1: (0, 2)   # player 0, card 2
            ...
            (0, 1): 0
            (0, 2): 1
            ...
        """
        matching = {}
        counter = 0
        
        for player_info in self.strategy.players_info:
            player_name= player_info.name
            if player_name == hinterName:
                # skip the hinter
                continue
            
            if player_name == self.name:
                hand = self.strategy.my_hand  # list of k elements (0 = the card exists but is unknown, null= there is no card anymore at that card_pos)
            else:
                hand = player_info.hand
            
            for (card_pos, card) in enumerate(hand):
                if card is not None:
                    matching[counter] = (player_name, card_pos)
                    matching[(player_name, card_pos)] = counter
                    counter += 1
        
        return matching
    
    
    def modulo(self, hinterName):
        """
        Returns the number of different choices for the integer that needs to be communicated.
        """
        # for our protocol, such number is the number of cards of the other players
        return len(self.relevant_cards(hinterName)) / 2
    
    
    def get_hint(self):
        """
        Compute hint to give.
        """
        x = self.compute_hash_sum(self.name) % self.modulo(self.name) # x is a number in range [0, tot_number_of_cards_of_other_players -1]
        # self.log("communicate message %d" % x)
        
        relevant_cards = self.relevant_cards(self.name) 
        player_name, card_pos = relevant_cards[x]
        
        matching = self.cards_to_hints(player_name)
        
        if card_pos in matching:
            hint_type, value = matching[card_pos]
            return player_name, value, hint_type
        
        else:
            # unable to give hint on that card
            return None, None, None
    
    
    def hint_to_integer(self, hinterName, info_action ):
        """
        Decode an HintAction and get my integer.
        """
        # this only makes sense if I am not the hinter
        assert self.name != hinterName
        
        # compute passed integer
        player_name = info_action.destination
        card_pos = self.hint_to_card(info_action)
        
        relevant_cards = self.relevant_cards(hinterName)
        x = relevant_cards[(player_name, card_pos)] # x -> integer that encodes (player, card_pos)
                
        # compute difference with other hashes. Modulo: #cards that the hinter sees
        y = (x - self.compute_hash_sum(hinterName)) % self.modulo(hinterName)
        
        return y
    
    
    def receive_hint(self, info_action):
        hinterName = info_action.source
        if self.name != hinterName:
            # I am not the hinter -> compute the hash of mu hand
            print("1)sono dentro receive hint, ora hint_to_integer")
            x = self.hint_to_integer(hinterName, info_action) # TODO: black magic understanding
            # 
            print("2)hint to integer fatto. ora Process hash [x]= ", x)
            data = self.process_hash(x, hinterName)
        else:
            data = None
        print("3)ora update_knowledge [data]= ", data)
        self.update_knowledge(hinterName, data)
        print("4)ora faccio receive hint base [data]= ", data)
        super(SumBasedHintsManager, self).receive_hint(info_action)
        

class CardHintsManager(SumBasedHintsManager):
    """
    Card hints manager.
    A hint communicates to every other player information about one of his cards.
    Specifically it says:
    - if the card is unseless;
    - which card is it (if it is playable or will be playable soon);
    - if the card will not be playable soon.
    """
    
    USELESS = 'Useless'
    HIGH_DISCARDABLE = 'High discardable'
    HIGH_RELEVANT = 'High relevant'
    
    
    def choose_card(self, target_name, turn):
        """
        Choose which of the target's cards receive a hint from the current player in the given turn.
        """
        if target_name == self.name:
            hand = self.strategy.my_hand
        else:
            target_index = self.players_names.index(target_name)
            hand = self.strategy.players_info[target_index].hand

        knowledge = self.knowledge[target_name]
        n = hash("%s,%d" % (target_name, turn))
        # get the lists of possible cards in the hand of the target -> cards not already exactly known and not already considered useless
        possible_cards = [card_pos for (card_pos, kn) in enumerate(knowledge) if hand[card_pos] is not None and not kn.knows_exactly() and not kn.useless]
        
        if len(possible_cards) == 0:
            # do not give hints
            return None
        
        # try to restrict to cards on which we don't know (almost) anything
        new_cards = [card_pos for card_pos in possible_cards if not knowledge[card_pos].high and not knowledge[card_pos].color and not knowledge[card_pos].value and not knowledge[card_pos].playable]
        if len(new_cards) > 0:
            return new_cards[n % len(new_cards)]
        
        # try to restrict to non-high cards
        new_cards = [card_pos for card_pos in possible_cards if not knowledge[card_pos].high]
        if len(new_cards) > 0:
            return new_cards[n % len(new_cards)]
        
        # try to restrict to cards on which we don't know (almost) anything apart from highness
        new_cards = [card_pos for card_pos in possible_cards if not knowledge[card_pos].color and not knowledge[card_pos].value and not knowledge[card_pos].playable]
        if len(new_cards) > 0:
            return new_cards[n % len(new_cards)]
        
        # no further restriction
        return possible_cards[n % len(possible_cards)]
    
    
    def hint_matching(self, board, kn, hinter_name): #kn: object knowledge referring to one specific card
        """
        Matching between integers and information about a card, which depends only on the board,
        the knowledge and the hinter.
        The information is of the form:
        - USELESS if the card is useless;
        - (color, number) if the card is playable or will be playable soon
                          (one of the two values can be None, if the player already knows something);
        - HIGH_DISCARDABLE if the card will not be playable soon, and is not relevant;
        - HIGH_RELEVANT if the card will not be playable soon, and is relevant.
        For example:
            0: USELESS
            1: HIGH_DISCARDABLE
            2: HIGH_RELEVANT
            3: (WHITE, 2)
            ...
            USELESS: 0
            HIGH_DISCARDABLE: 1
            HIGH_RELEVANT: 2
            (WHITE, 2): 3
            ...
        """
        
        matching = {}
        counter = 0
        
        # useless
        matching[counter] = self.USELESS
        matching[self.USELESS] = counter
        counter += 1
        
        # high discardable
        matching[counter] = self.HIGH_DISCARDABLE
        matching[self.HIGH_DISCARDABLE] = counter
        counter += 1
        
        # high relevant
        matching[counter] = self.HIGH_RELEVANT
        matching[self.HIGH_RELEVANT] = counter
        counter += 1
        
        if kn.color: # if the color is already known
            # communicate the number
            for number in range(1, self.strategy.NUM_NUMBERS + 1):
                if counter >= self.modulo(hinter_name):
                    # reached maximum number of information available
                    break
                matching[counter] = (None, number)
                matching[None, number] = counter
                counter += 1
        
        elif kn.value or kn.playable or kn.high:
            # communicate the color
            for color in self.strategy.COLORS:
                if counter >= self.modulo(hinter_name):
                    # reached maximum number of information available
                    break
                matching[counter] = (color, None)
                matching[color, None] = counter
                counter += 1

        else:
            # communicate both color and number
            fake_board = copy.copy(board)
            c = 0
            
            while counter < self.modulo(hinter_name) and sum(self.strategy.NUM_NUMBERS - len(n) for n in fake_board.items()) > 0:
                # pick next color
                color = self.strategy.COLORS[c % self.strategy.NUM_COLORS]
                c += 1
                
                number = len(fake_board[color]) + 1
                
                if number <= self.strategy.NUM_NUMBERS:
                    # this color still has useful cards!
                    matching[counter] = (color, number)
                    matching[(color, number)] = counter
                    counter += 1
                    fake_board[color].append(1)
        
        return matching
    
    
    def hash(self, hand, player_name, hinter_name):
        """
        hand *list of Cards sorted by card_pos"
        The hash of the hand that we want to communicate.
        Must be an integer.
        """
        card_pos = self.choose_card(player_name, self.strategy.turn)
        if card_pos is None:
            # no information
            return 0
        # hint_matching contains the list of possible hints the hinter name could give to the player_name based on the knowledge the player has to the given card at the moment
        matching = self.hint_matching(self.board, self.knowledge[player_name][card_pos], hinter_name)
        # hand: list of Cards the player_name has in this moment 
        card = hand[card_pos]
        
        if (card.color, card.value) in matching:
            # hint on the exact values
            return matching[card.color, card.value]
        
        elif (card.color, None) in matching:
            # hint on color
            return matching[card.color, None]
        
        elif (None, card.value) in matching:
            # hint on number
            return matching[None, card.value]
        
        elif not self.strategy.useful_card(card, self.board, self.full_deck_composition, self.strategy.discard_pile):
            # the card is useless
            return matching[self.USELESS]
        
        elif self.strategy.relevant_card(card, self.board, self.full_deck_composition, self.strategy.discard_pile):
            # the card is high and relevant
            return matching[self.HIGH_RELEVANT]
        
        else:
            # the card is high and discardable
            return matching[self.HIGH_DISCARDABLE]
    
    
    def hash_range(self, hinter_name):
        """
        Return H such that 0 <= hash < H.
        In this hints manager, the range is exactly how much information we can pass (but at least 3).
        """
        return max(self.modulo(hinter_name), 3)
    
    
    def process_hash(self, x, hinter_name):
        """
        Process the given hash of my hand, passed through a hint.
        Optionally, return data to be used by update_knowledge.
        """
        card_pos = self.choose_card(self.name, self.strategy.turn)
        if card_pos is None:
            # no information passed
            return None
        
        matching = self.hint_matching(self.board, self.knowledge[self.name][card_pos], hinter_name)
        information = matching[x]
        
        #self.log("obtained information about card %d, %r" % (card_pos, information))
        
        # update possibilities
        p = self.possibilities[card_pos] # p is a Counter with keys (color, value) and value= number of possibilities
        for card in self.full_deck_composition: # self.full_deck_composition counter of the full deck (color, value) = number of occurrencies
            if card in p:
                color = card[0]
                value = card[1]
                if information == self.USELESS: 
                    if self.strategy.useful_card(card, self.board, self.full_deck_composition, self.strategy.discard_pile):
                        del p[card]
                        # self.log("removing %r from position %d" % (card, card_pos))
                
                elif information == self.HIGH_RELEVANT:
                    if any(x in matching for x in [(color, value), (color, None), (None, value)]):
                        del p[card]
                        # self.log("removing %r from position %d" % (card, card_pos))
                    elif not  self.strategy.relevant_card(card, self.board, self.full_deck_composition, self.strategy.discard_pile):
                        del p[card]
                        # self.log("removing %r from position %d" % (card, card_pos))
                
                elif information == self.HIGH_DISCARDABLE:
                    if any(x in matching for x in [(color, value), (color, None), (None, value)]):
                        del p[card]
                        # self.log("removing %r from position %d" % (card, card_pos))
                    elif self.strategy.relevant_card(card, self.board, self.full_deck_composition, self.strategy.discard_pile):
                        del p[card]
                        # self.log("removing %r from position %d" % (card, card_pos))
                    elif not self.strategy.useful_card(card, self.board, self.full_deck_composition, self.strategy.discard_pile):
                        del p[card]
                        # self.log("removing %r from position %d" % (card, card_pos))
                
                else:
                    # I know the card exactly
                    color_info, value_info = information
                    if not (self.strategy.card_matches(card, (color_info, value_info))):
                        del p[card]
                        # self.log("removing %r from position %d" % (card, card_pos))
        
        return card_pos, information
    
    
    def update_knowledge(self, hinter_name, data=None):
        """
        Update knowledge after a hint has been given.
        Optionally, get data from process_hash.
        """
        
        if hinter_name != self.name and data is not None:
            # update my knowledge
            card_pos, information = data
            kn = self.knowledge[self.name][card_pos]
            
            if information == self.USELESS:
                kn.useless = True
            elif information == self.HIGH_RELEVANT or information == self.HIGH_DISCARDABLE:
                kn.high = True
            else:
                color, number = information
                if color is not None:
                    # I know the color
                    kn.color = True
                if number is not None:
                    # I know the number
                    kn.value = True
        
        
        # update knowledge of players different by me and the hinter
        for (player_name) in self.strategy.players_names:
            if player_name == hinter_name or player_name==self.name:
                # skip the hinter
                continue

            player_index = self.players_names.index(player_name)
            hand = self.strategy.players_info[player_index].hand
            card_pos = self.choose_card(player_name, self.strategy.turn)

            if card_pos is not None:
                card = hand[card_pos]
                kn = self.knowledge[player_name][card_pos]
                matching = self.hint_matching(self.board, kn, hinter_name)
                
                if (card.color, card.value) in matching:
                    # hint on the exact values
                    kn.color = True
                    kn.value = True
                
                elif (card.color, None) in matching:
                    # hint on color
                    kn.color = True
                
                elif (None, card.value) in matching:
                    # hint on number
                    kn.value = True
                
                elif not self.strategy.useful_card(card, self.board, self.full_deck_composition, self.strategy.discard_pile):
                    # the card is useless
                    kn.useless = True
                
                else:
                    # the card is high
                    kn.high = True