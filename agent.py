import random

from game import Player
import GameData


class Agent(Player):
    def __init__(self, name):
        super().__init__(name)
        self.ready = True
        self.index = None
        self.possibilities = None

    @staticmethod
    def playable_card(card, fireworks):
        if card.value == len(fireworks[card.color]) + 1:
            return True
        else:
            return False

    def dummy_agent_choice(self, observation):
        if observation['usedNoteTokens'] < 3 and random.randint(0, 2) == 0:
            # give random hint to the next player
            next_player_index = (observation['players'].index(self.name) + 1) % len(observation['players'])
            destination = observation['players'][next_player_index]
            card = random.choice([card for card in observation['playerHands'][next_player_index].hand
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

    # Rule based agent
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
            if k.color is not None:
                return GameData.ClientPlayerPlayCardRequest(self.name, own_card_knowledge.index(k))

        for k in own_card_knowledge:
            if k.value is not None:
                return GameData.ClientPlayerPlayCardRequest(self.name, own_card_knowledge.index(k))

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

            for index, (card, knowledge) in enumerate(zip(player_hand, player_knowledge)):
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
                for index, (card, knowledge) in enumerate(zip(player_hand, player_knowledge)):
                    if card.color is not color:
                        continue
                    if self.playable_card(card, fireworks) and knowledge.color is None:
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
                for index, (card, knowledge) in enumerate(zip(player_hand, player_knowledge)):
                    if card.value is not rank:
                        continue
                    if self.playable_card(card, fireworks) and knowledge.value is None:
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

    def rl_choice(self, observation):
        """
        Act by making a move, depending on the observations.
        :param observation: Dictionary containing all information over the Hanabi game, from the view of the players
        :return: Returns a dictionary, describing the action
        """

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
        if observation['usedNoteTokens'] > 1:
            isDiscardingAllowed = True
        else:
            isDiscardingAllowed = False
        if not isDiscardingAllowed:
            # Assume next player in turn is player on right
            # give a hint
            pass

        else:
            # Discard our oldest card
            return GameData.ClientPlayerDiscardCardRequest(self.name, 0)

    def set_index(self, index):
        self.index = index


class Knowledge:
    """
    An instance of this class represents what a player knows about a card, as known by everyone.
    """

    def __init__(self, color=None, value=None):
        self.color = color  # know the color
        self.value = value  # know the number
        self.playable = False  # at some point, this card was playable
        self.non_playable = False  # at some point, this card was not playable
        self.useless = False  # this card is useless
        self.high = False  # at some point, this card was high (relevant/discardable)(see CardHintsManager)

    def __repr__(self):
        return ("C" if self.color else "-") + ("N" if self.value else "-") + ("P" if self.playable else "-") + (
            "Q" if self.non_playable else "-") + ("L" if self.useless else "-") + ("H" if self.high else "-")

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
