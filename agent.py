import enum
import random

from game import Player
import GameData


class Agent(Player):
    def __init__(self, name):
        super().__init__(name)
        self.ready = True

    @staticmethod
    def playable_card(card, fireworks):
        if card.value == len(fireworks[card.color]) + 1:
            return True
        else:
            return False

    def dummy_agent_choice(self, game_state):
        if game_state['usedNoteTokens'] < 3 and random.randint(0, 2) == 0:
            # give random hint to the next player
            next_player_index = (game_state['players'].index(self.name) + 1) % len(game_state['players'])
            destination = game_state['players'][next_player_index]
            card = random.choice([card for card in game_state['playerHands'][next_player_index].hand
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

    def rule_based_choice(self):
        pass


class HanabiMoveType(enum.IntEnum):
    INVALID = 0
    PLAY = 1
    DISCARD = 2
    REVEAL_COLOR = 3
    REVEAL_RANK = 4
    DEAL = 5


class RuleBasedAgent(Player):
    def __init__(self, name):
        super().__init__(name)
        self.ready = True
        self.index = None
        self.rightPlayer = None
        self.leftPlayer = None

    @staticmethod
    def playable_card(card, fireworks):
        if card.value == len(fireworks[card.color]) + 1:
            return True
        else:
            return False

    def set_LR_players(self, index, idxL, idxR):
        self.index = index
        self.leftPlayer = idxL
        self.rightPlayer = idxR

    def check_if_not_playable_hint(self, observation):
        # check if rank hint was hinted for discard or not,
        last_move = observation['last_move']

        # for l in last_move:
        if last_move['player'] is not None:
            player = last_move['player']
            player_idx = None
            for i in range(len(observation['players'])):
                if observation['players'][i].name == player:
                    player_idx = i
            if last_move['move_type'] == HanabiMoveType.REVEAL_RANK and player_idx == self.leftPlayer and \
                    0 in last_move['card']:
                player_target_idx = (player_idx + 1) % len(observation['players'])
                # hint is from left partner, not useful hint though (just hint to free tokens)')
                for card_idx in last_move['card']:
                    observation['rankHintedButNoPlay'][player_target_idx][card_idx] = True
                # break
            elif last_move['move_type'] == HanabiMoveType.DISCARD or last_move['move_type'] == HanabiMoveType.PLAY:
                observation['rankHintedButNoPlay'][player_idx].pop(last_move['card'])
                observation['rankHintedButNoPlay'][player_idx].append(False)

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
            if k[2] is not None:
                # verify that index 0 correspond to the correct player
                observation['rankHintedButNoPlay'][self.index].pop(k[0])
                observation['rankHintedButNoPlay'][self.index].append(False)
                return GameData.ClientPlayerPlayCardRequest(self.name, k[0])

        for k in own_card_knowledge:
            if k[1] is not None and not observation['rankHintedButNoPlay'][self.index][k[0]]:
                observation['rankHintedButNoPlay'][self.index].pop(k[0])
                observation['rankHintedButNoPlay'][self.index].append(False)
                return GameData.ClientPlayerPlayCardRequest(self.name, k[0])

    def maybe_give_helpful_hint(self, observation):
        if observation['usedNoteTokens'] == 8:
            return None

        fireworks = observation['fireworks']

        best_so_far = 0
        player_to_hint = -1
        color_to_hint = -1
        value_to_hint = -1

        for player in observation['players']:
            player_hand = player.hand
            player_knowledge = []
            player_idx = observation['players'].index(player)
            for p in observation['playersKnowledge']:
                if p['player'] == player.name:
                    player_knowledge = p['knowledge']

            # Check if the card in the hand of the opponent is playable.
            card_is_really_playable = [False, False, False, False, False]
            playable_colors = []
            playable_ranks = []

            for _, (card, (index, val, color)) in enumerate(zip(player_hand, player_knowledge)):
                if self.playable_card(card, fireworks):
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
                for _, (card, (index, val, col)) in enumerate(zip(player_hand, player_knowledge)):
                    if card.color is not color:
                        continue
                    if self.playable_card(card, fireworks) and col is None:
                        information_content += 1
                    elif not self.playable_card(card, fireworks):
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
                for _, (card, (index, val, color)) in enumerate(zip(player_hand, player_knowledge)):
                    if card.value is not rank:
                        continue
                    if self.playable_card(card, fireworks) and \
                            (val is None or observation['rankHintedButNoPlay'][player_idx][index]):
                        information_content += 1
                    elif not self.playable_card(card, fireworks):
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
            return None
        elif color_to_hint is not None:
            return GameData.ClientHintData(self.name, player_to_hint, 'color', color_to_hint)
        elif value_to_hint != -1:
            return GameData.ClientHintData(self.name, player_to_hint, 'value', value_to_hint)
        else:
            return None

    def act(self, observation):
        """
        Act by making a move, depending on the observations.
        :param observation: Dictionary containing all information over the Hanabi game, from the view of the players
        :return: Returns a dictionary, describing the action
        """

        # check if in previous round, the left partner (index = num_players-1) has given us a VALUE-HINT, in which our
        # latest card (index = 0) was hinted. These cards are not necessarily playable, therefore they need to be marked
        self.check_if_not_playable_hint(observation)

        # If I have a playable card, play it.
        action = self.maybe_play_lowest_playable_card(observation)
        if action is not None:
            return action

        # Otherwise, if someone else has an unknown-playable card, hint it.
        action = self.maybe_give_helpful_hint(observation)
        if action is not None:
            return action

        # We couldn't find a good hint to give, or we are out of hint-stones.
        # We will discard a card, if possible.
        # Otherwise just hint the next play
        """isDiscardingAllowed = False
        for legal_moves in observation['legal_moves']:
            if legal_moves['action_type'] is 'DISCARD':
                isDiscardingAllowed = True
                break """
        if observation['usedNoteTokens'] > 1:
            isDiscardingAllowed = True
        else:
            isDiscardingAllowed = False
        if not isDiscardingAllowed:
            # Assume next player in turn is player on right
            hand_on_right = observation['players'][self.rightPlayer].hand
            return GameData.ClientHintData(self.name, observation['players'][self.rightPlayer].name, 'value',
                                           hand_on_right[0].value)
        else:
            # Discard our oldest card
            observation['rankHintedButNoPlay'][self.index].pop(0)
            observation['rankHintedButNoPlay'][self.index].append(False)
            return GameData.ClientPlayerDiscardCardRequest(self.name, 0)


"""if __name__ == "__main__":
    agent = RuleBasedAgent("Lise")

    player = Player("matt")

    observation = {
        'current_player': agent,  # should return the player name
        'usedStormTokens': 0,
        'usedNoteTokens': 0,
        'players': [agent, player],
        'num_players': 2,
        # 'deck_size': self.deck_size,
        'fireworks': [],
        # 'legal_moves': self.get_legal_moves(),
        'discard_pile': data.discardPile,
        'hints': hintState,
        'playersKnowledge': playersKnowledge,
        'rankHintedButNoPlay': rankHintedButNoPlay,
        'last_move': lastMove
    }

    agent.act(observation)"""
