import random


class HintsManager(object):
    """
    Hints Manager.
    """

    def __init__(self, agent):
        self.agent = agent

    def received_hint(self, destination, hint_type, value, positions):
        """
        Update the possibilities after a hint was given to the agent
        @param destination: the player to which the hint is destined
        @param hint_type: the type of hint (value or color)
        @param value: the value of the hint (number or color depending on the type)
        @param positions: the positions of the card in the hand associated with the hint
        """
        if destination == self.agent.name:
            for (i, p) in enumerate(self.agent.possibilities):
                for card in self.agent.full_deck_composition:
                    # Check if the card matches the hint
                    matches = True
                    if hint_type == "color" and card[0] != value:
                        matches = False
                    elif hint_type == "value" and card[1] != value:
                        matches = False
                    hinted_card = (i in positions and matches)
                    not_hinted_card = (i not in positions and not matches)
                    match = hinted_card or not_hinted_card
                    if not match and card in p:
                        # we only keep in the possibilities the cards that confirm the hint given
                        del p[card]

    def give_helpful_hint(self, observation):
        """
        Try to complete a hint to give to a player full knowledge of at least one of its playable cards
        @param observation: current state of the game
        @return: a helpful hint if one can be given, None otherwise
        """
        fireworks = observation['fireworks']
        best_so_far = 0
        player_to_hint = -1
        color_to_hint = -1
        value_to_hint = -1

        for player in observation['players']:
            player_name = player.name
            if player_name == self.agent.name:
                break
            player_knowledge = observation['playersKnowledge'][player_name]
            player_hand = player.hand

            # Check if the card in the hand of the player is playable
            card_is_really_playable = [False, False, False, False, False]
            playable_colors = []
            playable_ranks = []

            for index, (card, knowledge) in enumerate(zip(player_hand, player_knowledge)):
                if not knowledge.knows("color") and not knowledge.knows("value"):
                    continue
                if self.agent.playable_card(card, fireworks):
                    card_is_really_playable[index] = True
                    if card.color not in playable_colors:
                        playable_colors.append(card.color)
                    if card.value not in playable_ranks:
                        playable_ranks.append(card.value)

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

        if best_so_far == 0:
            return None, None, None
        elif color_to_hint is not None:
            return player_to_hint, color_to_hint, "color"
        elif value_to_hint != -1:
            return player_to_hint, value_to_hint, "value"
        else:
            return None, None, None

    def give_useful_hint(self, observation):
        """
        Try to give information about a card that is playable
        @param observation: current state of the game
        @return: a useful hint if one can be given, None otherwise
        """
        fireworks = observation['fireworks']

        for player in observation['players']:
            player_name = player.name
            if player_name == self.agent.name:
                break
            player_knowledge = observation['playersKnowledge'][player_name]
            hand = player.hand

            for card_pos, card in enumerate(hand):
                if self.agent.playable_card(card, fireworks):
                    knowledge = player_knowledge[card_pos]
                    if knowledge.knows("color") and knowledge.knows("value"):
                        continue
                    if knowledge.knows("value"):
                        hint_type = "color"
                        value = card.color
                    else:
                        hint_type = "value"
                        value = card.value
                    return player_name, value, hint_type
        return None, None, None

    def tell_most_information(self, observation, threshold=0):
        """
        Give information about the color/value that has the most occurrences in the hand of a player across all players
        with a tolerance of at least threshold
        @param observation: current state of the game
        @param threshold: minimum number of cards that must be concerned by the hint
        @return: hint that concerns the value/color most represented and concerning at least threshold in a player hand
                 if possible, None otherwise
        """
        unknown_color = {'red': 0, 'blue': 0, 'yellow': 0, 'white': 0, 'green': 0}
        unknown_value = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        max_color_occurrences = max_value_occurrences = 0
        destination_name_color = destination_name_value = value_color = value_value = None

        for player_info in observation['players']:
            if player_info.name == self.agent.name:
                continue
            player_knowledge = observation['playersKnowledge'][player_info.name]
            for index, (card, knowledge) in enumerate(zip(player_info.hand, player_knowledge)):
                if knowledge.knows("color") and knowledge.knows("value"):
                    continue
                elif knowledge.knows("color"):
                    unknown_value[card.value] += 1
                elif knowledge.knows("value"):
                    unknown_color[card.color] += 1
                else:
                    unknown_value[card.value] += 1
                    unknown_color[card.color] += 1
            max_color_occurrences_player = max(unknown_color.values())
            max_value_occurrences_player = max(unknown_value.values())

            if max_color_occurrences_player > max_color_occurrences:
                max_color_occurrences = max_color_occurrences_player
                destination_name_color = player_info.name
                value_color = max(unknown_color, key=unknown_color.get)

            if max_value_occurrences_player > max_value_occurrences:
                max_value_occurrences = max_value_occurrences_player
                destination_name_value = player_info.name
                value_value = max(unknown_value, key=unknown_value.get)

        if max_color_occurrences < threshold and max_value_occurrences < threshold:
            return None, None, None

        if max_color_occurrences >= max_value_occurrences:
            hint_type = "color"
            value = value_color
            destination_name = destination_name_color
        else:
            hint_type = "value"
            value = value_value
            destination_name = destination_name_value

        return destination_name, value, hint_type

    def tell_unknown(self, observation):
        """
        Give information that is not known yet to a random player prioritizing color
        @param observation: current state of the game
        @return: information obout an unknown characteristic of a card if possible, None otherwise
        """
        destination = self.agent
        while destination == self.agent:
            destination = self.agent.players[random.randint(0, len(self.agent.players) - 1)]
        destination_hand = destination.hand

        for idx, kn in enumerate(observation['playersKnowledge'][destination.name]):
            if not kn.knows("color"):
                hint_type = "color"
                value = destination_hand[idx].color
                return destination.name, value, hint_type
            if not kn.knows("value"):
                hint_type = "value"
                value = destination_hand[idx].value
                return destination.name, value, hint_type
        return None, None, None

    def tell_useless(self, observation):
        """
        Give information about a useless card
        @param observation: current state of the game
        @return: information about a useless card if there is, None otherwise
        """
        for player in observation['players']:
            player_name = player.name
            if player_name == self.agent.name:
                break
            player_knowledge = observation['playersKnowledge'][player_name]
            for card_pos, card in enumerate(player.hand):
                if not self.agent.useful_card((card.color, card.value), observation['fireworks'],
                                              self.agent.full_deck_composition,
                                              self.agent.counterOfCards(observation['discard_pile'])):
                    knowledge = player_knowledge[card_pos]
                    if knowledge.knows("color") and knowledge.knows("value"):
                        continue
                    if knowledge.knows("value"):
                        hint_type = "color"
                        value = card.color
                    else:
                        hint_type = "value"
                        value = card.value
                    return player_name, value, hint_type
        return None, None, None

    def tell_ones(self):
        """
        Give information about cards with value 1
        @return: information about cards with value 1 if there are, None otherwise
        """
        destination = self.agent
        while destination == self.agent:
            destination = self.agent.players[random.randint(0, len(self.agent.players) - 1)]
        destination_hand = destination.hand

        for card in destination_hand:
            if card.value == 1:
                return destination.name, card.value, "value"
        return None, None, None

    def tell_fives(self):
        """
        Give information about cards with value 5
        @return: information about cards with value 5 if there are, None otherwise
        """
        destination = self.agent
        while destination == self.agent:
            destination = self.agent.players[random.randint(0, len(self.agent.players) - 1)]
        destination_hand = destination.hand

        for card in destination_hand:
            if card.value == 5:
                return destination.name, card.value, "value"
        return None, None, None

    def tell_randomly(self):
        """
        Give information about random card(s)
        @return: information about random card(s)
        """
        destination = self.agent
        while destination == self.agent:
            destination = self.agent.players[random.randint(0, len(self.agent.players) - 1)]
        destination_hand = destination.hand

        card = random.choice([card for card in destination_hand if card is not None])
        if random.randint(0, 1) == 0:
            hint_type = "color"
            value = card.color
        else:
            hint_type = "value"
            value = card.value
        return destination.name, value, hint_type
