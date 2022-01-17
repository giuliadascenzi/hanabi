#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import sys
import itertools
import copy
import GameData

class PlayManager(object):
    """
    PlayManager.
    """
    def __init__(self, agent):
        self.agent = agent    # my agent object

    def play_best_safe_card(self, observation):
        WEIGHT = {number: self.agent.NUM_NUMBERS - number for number in range(1, self.agent.NUM_NUMBERS)}
        WEIGHT[self.agent.NUM_NUMBERS] = self.agent.NUM_NUMBERS

        tolerance = 1e-3
        best_card_pos = None
        best_avg_num_playable = -1.0  # average number of other playable cards, after my play
        best_avg_weight = 0.0  # average weight (in the sense above)
        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p = Counter of possible tuple (card,value)
            if all(self.agent.is_playable(card, observation['fireworks']) for card in p) and len(p) > 0:
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
                        num_playable.append(sum(1 for player_info in observation['players'] for c in player_info.hand if
                                                c is not None and self.agent.playable_card(c, fake_board)))

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
        else:
            return best_card_pos


    def play_safe_card_prob(self, observation, prob):
        WEIGHT = {number: self.agent.NUM_NUMBERS - number for number in range(1, self.agent.NUM_NUMBERS)}
        WEIGHT[self.agent.NUM_NUMBERS] = self.agent.NUM_NUMBERS

        tolerance = 1e-3
        best_card_pos = None
        best_avg_num_playable = -1.0  # average number of other playable cards, after my play
        best_avg_weight = 0.0  # average weight (in the sense above)
        best_probability = 0
        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p = Counter of possible tuple (color,value)
            tot_playable = sum(p[card] if self.agent.is_playable(card, observation['fireworks']) else 0 for card in p)
            tot_possibility = sum(p.values())
            probability = tot_playable/tot_possibility
            if len(p) > 0 and probability >= prob:
                # the card in this position is playable with probability prob!
                # how many cards of the other players become playable, on average?
                num_playable = []
                for card in p:
                    assert p[card]>0
                    # Remember that p is a tuple (color, value)
                    color = card[0]
                    value = card[1]
                    fake_board = copy.copy(observation['fireworks'])
                    fake_board[color].append(value)
                    for i in range(p[card]):
                        num_playable.append(sum(1 for player_info in observation['players'] for c in player_info.hand if
                                                c is not None and self.agent.playable_card(c, fake_board)))

                avg_num_playable = float(sum(num_playable)) / len(num_playable)
                avg_weight = float(sum(WEIGHT[card[1]] * p[card] for card in p)) / sum(p.values())
                if probability> best_probability and (avg_num_playable > best_avg_num_playable + tolerance or \
                        avg_num_playable > best_avg_num_playable - tolerance and avg_weight > best_avg_weight):
                    #print("update card to be played, pos %d, score %f, %f" % (card_pos, avg_num_playable, avg_weight))
                    best_card_pos, best_avg_num_playable, best_avg_weight, best_probability = card_pos, avg_num_playable, avg_weight, probability

        if best_card_pos is not None:
            #print("playing card in position %d gives %f playable cards on average and weight %f" % (
            #    best_card_pos, best_avg_num_playable, best_avg_weight))
            return best_card_pos
        else:
            return best_card_pos

    def play_oldest(self):
        return 0

    # Not used but put here in case we want to use it anyway
    def maybe_play_lowest_playable_card(self, observation):
        """
        It previously a card has been hinted to him,
        :param observation:
        :return: card_pos #TODO: maybe check also the possibilities? maybe the hint meant that that card was useless not playable?
        """
        own_card_knowledge = []
        for p in observation['playersKnowledge']:
            if p['player'] == self.agent.name:
                own_card_knowledge = p['knowledge']

        for k in own_card_knowledge:
            if k.color is not None:
                return own_card_knowledge.index(k)

        for k in own_card_knowledge:
            if k.value is not None:
                return own_card_knowledge.index(k)
        else:
            return None