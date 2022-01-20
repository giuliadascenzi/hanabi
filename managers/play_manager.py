import copy


class PlayManager(object):
    """
    Play Manager.
    """

    def __init__(self, agent):
        self.agent = agent

    def play_best_card_prob(self, observation, prob):
        """
        Look for the best card to play (best means the card that would transform more cards in other
        players hands to playable) that is playable up until probability prob
        @param observation: current state of the game
        @param prob: probability up until which the card is playable
        @return: best card playable to play if it exists, None otherwise
        """
        # Weights (value 1 : weight 4) (value 2: weight 3) (value 3: weight 2) (value 4: weight 1) (value 5: weight: 5)
        WEIGHT = {number: self.agent.NUM_NUMBERS - number for number in range(1, self.agent.NUM_NUMBERS)}
        WEIGHT[self.agent.NUM_NUMBERS] = self.agent.NUM_NUMBERS
        ### HOW TO CHOOSE THE BEST CARD TO PLAY?
        # 1) the probability of the given card of being playable must be higher then the threshold
        # 2) In case of tie choose the card that would make the highest number of other players cards playable
        # 3) consider a different weight connected to the value of the card
        tolerance = 1e-3
        best_card_pos = None
        best_avg_num_playable = -1.0
        best_avg_weight = 0.0
        best_probability = 0

        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p = Counter of possible tuple (color,value)
            # 1) Define the probability of the card being playable considering all the possible (color,value) instances that the card could be
            tot_playable = sum(p[card] if self.agent.playable_card(card, observation['fireworks']) else 0 for card in p) # count the # possible instances that would lead to a playable card
            tot_possibility = sum(p.values()) # total possibilities of the card
            if tot_playable == 0:
                probability = 0
            else:
                probability = float(tot_playable / tot_possibility)
            if len(p) > 0 and probability >= prob:
                num_playable = []  # how many cards of the other players become playable, on average?
                for card in p:
                    assert p[card] > 0
                    color = card[0]
                    value = card[1]
                    fake_board = copy.deepcopy(observation['fireworks'])
                    fake_board[color].append(value)
                    assert (fake_board != observation['fireworks'])

                    for i in range(p[card]):
                        num_playable.append(sum(1 for player_info in observation['players'] for c in player_info.hand if self.agent.playable_card(c, fake_board)))
                    
                    
                
                avg_num_playable = float(sum(num_playable)) / len(num_playable) # weighted average of number of cards that would become playable = sum ( #possibility * #card that would become playable) / #possibilities of that card
                avg_weight = float(sum(WEIGHT[card[1]] * p[card] for card in p)) / sum(p.values())  # compute the avg weight of the given card considering all the possible values associated with it 

                if probability > best_probability or ( probability == best_probability and 
                                                        avg_num_playable > best_avg_num_playable + tolerance or
                                                        avg_num_playable > best_avg_num_playable - tolerance and 
                                                        avg_weight > best_avg_weight):
                    best_card_pos, best_avg_num_playable, best_avg_weight, best_probability = card_pos, \
                                                                                              avg_num_playable, \
                                                                                              avg_weight, \
                                                                                              probability
        return best_card_pos

    @staticmethod
    def play_oldest():
        return 0
