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
    
    def is_usable(self, hinter_id):
        """
        Check that it is possible to pass all the information.
        """
        return True
    
    def receive_hint(self, destination, type, value, positions):
        """
        Receive hint given to the destination update knowledge. 
        info_action is an object returned by the server after each hint
        """
        if destination == self.agent.name:
            # process direct hint
             for (i, p) in enumerate(self.agent.possibilities):
                for card in self.agent.full_deck_composition:
                    if not self.card_matches_hint(card, type, value, positions, i) and card in p:
                        # removing card from position  due to hint" 
                        del p[card]
    
    def card_matches_hint(self, card, type, value, positions, card_pos):
        # does this card (in the given position) match the given hint?
        matches = self.card_matches(card, type, value)
        # card in a hinted position with a possible value that matches the hint
        hinted_card = (card_pos in positions and matches)
        not_hinted_card = (card_pos not in positions and not matches)
        return hinted_card or not_hinted_card

    @staticmethod
    def card_matches(card, type, value):
        # does this card match the given color/number? (if the value is None, it is considered to match) 
        if type == "color" and card[0] != value:
            return False
        elif type == "value" and card[1] != value:
            return False
        return True

    def get_hint(self, observation):
        """
        Compute hint to give.
        """
        destination_name, value, type = self.maybe_give_helpful_hint(observation)
        return destination_name, value, type

    def maybe_give_helpful_hint(self, observation):
        fireworks = observation['fireworks']

        best_so_far = 0
        player_to_hint = -1
        color_to_hint = -1
        value_to_hint = -1

        for player in observation['players']:
            player_hand = player.hand
            player_knowledge = observation['playersKnowledge'][player.name]
            # player_idx = observation['players'].index(player)
            
            # Check if the card in the hand of the opponent is playable.
            card_is_really_playable = [False, False, False, False, False]
            playable_colors = []
            playable_ranks = []
            
            for index, (card, knowledge) in enumerate(zip(player_hand, player_knowledge)):
                # if the player does not know anything about the card skip it
                if not knowledge.knows("color") and not knowledge.knows("value"):
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
                for index, (card, knowledge) in enumerate(zip(player_hand, player_knowledge)):
                    if card.color is not color:
                        continue
                    if self.agent.playable_card(card, fireworks) and knowledge.color is False:
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
                for index, (card, knowledge) in enumerate(zip(player_hand, player_knowledge)):
                    if card.value is not rank:
                        continue
                    if self.agent.playable_card(card, fireworks) and knowledge.value is False:
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
            return player_to_hint, color_to_hint, "color"
        elif value_to_hint != -1:
            return player_to_hint, value_to_hint, "value"
        else:
            return None, None, None

    def get_low_value_hint(self, observation):
        destination_name = self.agent.name
        while destination_name == self.agent.name:
            destination_name = self.agent.players_names[random.randint(0, len(observation['players'])-1)]
        destination_hand = ""
        for player_info in observation['players']:
            if player_info.name == destination_name:
                destination_hand = player_info.hand
        
        # card = random.choice([card for card in destination_hand if card is not None])
        destination_hand.sort(key=lambda c: c.value)
        card = destination_hand[0]
        
        if random.randint(0, 1) == 0:
            type = "color"
            value = card.color
        else:
            type = "value"
            value = card.value
        
        return destination_name, value, type

    def is_duplicate(self, card, observation):
        """
        Says if the given card is owned by some player who knows everything about it.
        """
        # check other players' hands
        for (player_info) in observation['players']:
            hand = player_info.hand
            player_name = player_info.name
            for card_pos in range(self.agent.num_cards):
                kn = observation['playersKnowledge'][player_name][card_pos]
                if kn.knows_exactly() and hand[card_pos] is not None and hand[card_pos].equals(card):
                    return True

        # check my hand
        for card_pos in range(self.agent.num_cards):
            kn = self.agent.knowledge[self.agent.name][card_pos]
            if kn.knows_exactly() and any(card.equals(c) for c in self.agent.possibilities[card_pos]):
                return True

        return False

    def is_duplicate(self, card):
        """
        Says if the given card is owned by some player who knows everything about it.
        """
        # check other players' hands
        for (player_id, hand) in self.agent:
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
    
    def tell_unknown(self, observation):
        '''Tell a random player an unknown information prioritizing color'''
        destination_name = self.agent.name
        while destination_name == self.agent.name:
            destination_name = self.agent.players_names[random.randint(0, len(observation['players'])-1)]
        for player_info in observation['players']:
            if player_info.name == destination_name:
                destination_hand = player_info.hand
            
        for idx, kn in enumerate(observation['playersKnowledge'][destination_name]):
            if kn.color == False:
                type = "color"
                value = destination_hand[idx].color
                return destination_name, value, type
            if kn.value == False:
                type = "value"
                value = destination_hand[idx].value
                return destination_name, value, type
        return None, None, None

    def tell_most_information(self, observation):
        pass

    def tell_randomly(self, observation):
        '''Tell to a random player a random information prioritizing color'''
        destination_name = self.agent.name
        while destination_name == self.agent.name:
            destination_name = self.agent.players_names[random.randint(0, len(observation['players'])-1)]
        for player_info in observation['players']:
            if player_info.name == destination_name:
                destination_hand = player_info.hand
            
        card = random.choice([card for card in destination_hand if card is not None])
        if random.randint(0, 1) == 0:
            type = "color"
            value = card.color
        else:
            type = "value"
            value = card.value
        return destination_name, value, type

    def tell_fives(self, observation):
        '''Tell 5s to a random player if it has them'''
        destination_name = self.agent.name
        while destination_name == self.agent.name:
            destination_name = self.agent.players_names[random.randint(0, len(observation['players'])-1)]

        for player_info in observation['players']:
            if player_info.name == destination_name:
                destination_hand = player_info.hand
        for card in destination_hand:
            if card.value == 5:
                return destination_name, card.value, "value"
        return None, None, None

    def tell_fives(self, observation):
        '''Tell 1s to a random player if it has them'''
        destination_name = self.agent.name
        while destination_name == self.agent.name:
            destination_name = self.agent.players_names[random.randint(0, len(observation['players'])-1)]

        for player_info in observation['players']:
            if player_info.name == destination_name:
                destination_hand = player_info.hand
        for card in destination_hand:
            if card.value == 1:
                return destination_name, card.value, "value"
        return None, None, None