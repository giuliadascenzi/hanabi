import random
from game import Player
import GameData



class Agent(Player):
    def __init__(self, name):
        super().__init__(name)
        self.ready = True

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
        """Act based on an observation."""

        if observation['current_player_offset'] != 0:
            return None

        # Check if there are any pending hints and play the card corresponding to the hint.
        for card_index, hint in enumerate(observation['card_knowledge'][0]):
            if hint['color'] is not None or hint['rank'] is not None:
                return GameData.ClientPlayerPlayCardRequest(self.name, card_index).serialize()

        # Check if it's possible to hint a card to your colleagues.
        fireworks = observation['fireworks']
        if observation['information_tokens'] > 0:
            # Check if there are any playable cards in the hands of the opponents.
            for player_offset in range(1, observation['num_players']):
                player_hand = observation['observed_hands'][player_offset]
                player_hints = observation['card_knowledge'][player_offset]
                # Check if the card in the hand of the opponent is playable.
                for card, hint in zip(player_hand, player_hints):
                    if (card.value == fireworks[card.color]) and (hint['color'] is None):
                        player_name = observation['players'][player_offset]
                        return GameData.ClientHintData(self.name, player_name, 'color', card['color']).serialize()

        # If not then discard or play card number 0
        if observation['usedNoteTokens'] > 1:
            return GameData.ClientPlayerDiscardCardRequest(self.name, 0).serialize()
        else:
            return GameData.ClientPlayerPlayCardRequest(self.name, 0).serialize()
