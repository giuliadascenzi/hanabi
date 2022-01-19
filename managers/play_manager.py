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
        WEIGHT = {number: self.agent.NUM_NUMBERS - number for number in range(1, self.agent.NUM_NUMBERS)}
        WEIGHT[self.agent.NUM_NUMBERS] = self.agent.NUM_NUMBERS
        tolerance = 1e-3
        best_card_pos = None
        best_avg_num_playable = -1.0
        best_avg_weight = 0.0
        best_probability = 0

        for (card_pos, p) in enumerate(self.agent.possibilities):
            # p = Counter of possible tuple (color,value)
            tot_playable = sum(p[card] if self.agent.is_playable(card, observation['fireworks']) else 0 for card in p)
            tot_possibility = sum(p.values())
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
                        num_playable.append(sum(1 for player_info in observation['players'] for c in player_info.hand if
                                                c is not None and self.agent.playable_card(c, fake_board)))

                avg_num_playable = float(sum(num_playable)) / len(num_playable)
                avg_weight = float(sum(WEIGHT[card[1]] * p[card] for card in p)) / sum(p.values())

                if probability > best_probability or (
                        probability == best_probability and avg_num_playable > best_avg_num_playable + tolerance or
                        avg_num_playable > best_avg_num_playable - tolerance and avg_weight > best_avg_weight):
                    best_card_pos, best_avg_num_playable, best_avg_weight, best_probability = card_pos, \
                                                                                              avg_num_playable, \
                                                                                              avg_weight, probability
        return best_card_pos

    @staticmethod
    def play_oldest():
        return 0
