#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import sys
import itertools
import copy
import GameData

class HintsManager(object):
    """
    HintsManager.
    """
    def __init__(self, agent):
        self.agent = agent    # my agent object

    '''      
    def is_duplicate(self, card):
        """
        Says if the given card is owned by some player who knows everything about it.
        """
        # check other players' hands
        for (player_id, hand) in self.agent.hands.iteritems():
            for card_pos in range(self.k):
                kn = self.agent.knowledge[player_id][card_pos]
                if kn.knows_exactly() and hand[card_pos] is not None and hand[card_pos].equals(card):
                    return True
        
        # check my hand
        for card_pos in range(self.k):
            kn = self.agent.knowledge[self.id][card_pos]
            if kn.knows_exactly() and any(card.equals(c) for c in self.agent.possibilities[card_pos]):
                return True
        
        return False
    '''  
    
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
        if info_action.destination == self.agent.name:
            # process direct hint
             for (i, p) in enumerate(self.agent.possibilities):
                for card in self.agent.full_deck_composition:
                    if not self.card_matches_hint(card, info_action, i) and card in p:
                        # self.log("removing card %r from position %d due to hint" % (card, i))
                        del p[card]
        
        # update knowledge
        for card_pos in info_action.positions:
            kn = self.agent.knowledge[info_action.destination][card_pos]
            if info_action.type == "color":
                kn.color = True
            else:
                kn.value = True
        
        
        
    
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
        
        observation = {
                   # 'current_player': data.currentPlayer,  # should return the player name
                    'usedStormTokens': self.agent.usedStormTokens,
                    'usedNoteTokens': self.agent.usedNoteTokens,
                    'players': self.agent.players_info,
                    'num_players': self.agent.num_players,
                    # 'deck_size': self.deck_size,
                    'fireworks': self.agent.board,
                    # 'legal_moves': self.get_legal_moves(),
                    'discard_pile': self.agent.discard_pile,
                    #'hints': hintState,
                    'playersKnowledge': self.agent.knowledge,
                    #'rankHintedButNoPlay': rankHintedButNoPlay,
                    #'last_move': lastMove
                }
        destination_name, value, type = self.maybe_give_helpful_hint(observation)
        return destination_name, value, type
    

    def maybe_give_helpful_hint(self, observation):

        # give a hint that will make a card playable
        assert observation['usedNoteTokens'] != 8


        fireworks = observation['fireworks']

        best_so_far = 0
        player_to_hint = -1
        color_to_hint = -1
        value_to_hint = -1

        for player in observation['players']:
            player_hand = player.hand
            player_knowledge = observation['playersKnowledge'][player.name]
            #player_idx = observation['players'].index(player)
            
            # Check if the card in the hand of the opponent is playable.
            card_is_really_playable = [False, False, False, False, False]
            playable_colors = []
            playable_ranks = []
            
            for index, (card, kn) in enumerate(zip(player_hand, player_knowledge)):
                # if the player does not know anything about the card skip it
                if (not kn.knows("color") and not kn.knows("value") ):
                    continue
                if self.agent.playable_card(card, fireworks):
                    card_is_really_playable[index] = True
                    if card.color not in playable_colors:
                        playable_colors.append(card.color)
                    if card.value not in playable_ranks:
                        playable_ranks.append(card.value)

            '''Can we construct a color hint that gives our partner information about unknown - playable cards, 
            without also including any unplayable cards?'''

            # go through playable colors
            for color in playable_colors:
                information_content = 0
                missInformative = False
                for index, (card, kn) in enumerate(zip(player_hand, player_knowledge)):
                    if card.color is not color:
                        continue
                    if self.agent.playable_card(card, fireworks) and kn.color is False:
                        information_content += 1
                    elif not self.agent.playable_card(card, fireworks):
                        missInformative = True
                        break
                if missInformative:
                    continue
                if information_content > best_so_far:
                    best_so_far = information_content
                    color_to_hint = color
                    value_to_hint = -1
                    player_to_hint = player.name

            # go through playable ranks
            for rank in playable_ranks:
                information_content = 0
                missInformative = False
                for index, (card, kn) in enumerate(zip(player_hand, player_knowledge)):
                    if card.value is not rank:
                        continue
                    if self.agent.playable_card(card, fireworks) and kn.value is False:
                        information_content += 1
                    elif not self.agent.playable_card(card, fireworks):
                        missInformative = True
                        break
                if missInformative:
                    continue
                if information_content > best_so_far:
                    best_so_far = information_content
                    color_to_hint = None
                    value_to_hint = rank
                    player_to_hint = player.name

        # went through all players, now check
        if best_so_far == 0:
            return None, None, None
        elif color_to_hint is not None:
            return (player_to_hint, color_to_hint, "color")
        elif value_to_hint != -1:
            return (player_to_hint, value_to_hint, "value")
        else:
            return None, None, None


    def get_low_value_hint(self):
        
        destination_name = self.agent.name
        while (destination_name== self.agent.name):
            destination_name = self.agent.players_names[random.randint(0,self.agent.num_players-1)]
        destination_hand = ""
        for player_info in self.agent.players_info:
            if player_info.name== destination_name:
                destination_hand= player_info.hand
        
        #card = random.choice([card for card in destination_hand if card is not None])
        destination_hand.sort(key = lambda c: c.value)
        card = destination_hand[0]

        
        if random.randint(0,1) == 0:
            type= "color"
            value = card.color
        else:
            type=  "value"
            value = card.value
        
        return destination_name, value, type