import GameData
import random
import copy

'''k
  - play_best_card_prob(self, observation, prob)
  - play oldest

  - give_helpful_hint(agent, observation):
  - give_useful_hint(agent, observation):
  - tell_most_information(agent, observation):
  - tell_unknown(agent, observation): 
  - tell_useless(agent, observation):
  - tell_ones(agent, observation):
  - tell_fives(agent, observation):
  - tell_randomly(agent, observation)

  - discard_useless_card(agent, observation, lowest=False):
  - discard_less_relevant(agent, observation):
  - discard_duplicate_card(agent, observation):
  - discard_randomly(self):
  - discard_oldest():'''

class Ruleset:

    def __init__(self):
        self.rules = {
            0: self.play_best_card_prob,
            1: self.give_helpful_hint,
            2: self.tell_randomly,
            3: self.tell_fives,
            4: self.tell_ones,
            5: self.tell_unknown,
            6: self.discard_useless_card,
            7: self.discard_less_relevant,
            8: self.discard_duplicate_card
        }
        self.active_rules = list(self.rules.keys())
        self.fittest_ruleset = []
        self.best_score = 0

    def shuffle_rules(self):
        random.shuffle(self.active_rules)

    def fitness(self, avg_score):
        if avg_score > self.best_score:
            self.best_score = avg_score
            self.fittest_ruleset = copy.deepcopy(self.active_rules)
            # Make it print the fittest
            with open("fittest_ruleset.txt", "a") as f:
                f.write(str(self.best_score))
                f.write("\n")
                f.write(', '.join(str(rule) for rule in self.fittest_ruleset))
                f.write("\n---------\n")

    ###############
    # PLAY RULES
    ###############

    @staticmethod
    def play_best_card_prob(agent, observation, prob):
        """
        Plays the best card (best means the card that would transform more cards in other players hands to playable)
        that is playable up until probability prob, if possible
        @param agent: the player that will try to play a card
        @param observation: current state of the game
        @param prob: probability up until which a card is playable
        @return: a request to play the best card, None if it is not possible
        """
        card_pos = agent.card_play_manager.play_best_card_prob(observation, prob)
        if card_pos is not None:
            print(">>>play probable safe card: ", card_pos)
            return GameData.ClientPlayerPlayCardRequest(agent.name, card_pos)
        return None

    @staticmethod
    def play_oldest(agent):
        """
        Plays the oldest card in the hand
        @param agent: the player that will try to play a card
        @return: a request to play the oldest card
        """
        card_pos = agent.card_play_manager.play_oldest()
        print(">>>play oldest card: ", card_pos)
        return GameData.ClientPlayerPlayCardRequest(agent.name, card_pos)

    ###############
    # HINT RULES
    ###############

    @staticmethod
    def give_helpful_hint(agent, observation):
        """
        Give an helpful hint (which is a hint that will allow a player to have full knowledge of one of its playable
        cards, at least), if possible
        @param agent: the player that will try to hint
        @param observation: current state of the game
        @return: a request to hint, None if it is not possible
        """
        if observation['usedNoteTokens'] < 8:
            destination_name, value, hint_type = agent.card_hints_manager.give_helpful_hint(observation)
            if (destination_name, value, hint_type) != (None, None, None):
                print(">>>give the helpful hint ", hint_type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, hint_type, value)
        return None

    @staticmethod
    def give_useful_hint(agent, observation):
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.give_useful_hint(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the useful hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_most_information(agent, observation, threshold=0):
        '''Tell most information to a random player'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_most_information(observation, threshold)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the most information hint to a player ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    # Prioritize color, just next player is considered
    @staticmethod
    def tell_unknown(agent, observation):
        '''Tell a random player an unknown information prioritizing color'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_unknown(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the tell_unknow hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_anyone_useless_card(agent, observation):
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_useless(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the tell_useless hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_ones(agent, observation):
        '''Tell 1s to a random player if it has them'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_ones(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the tell_ones hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_fives(agent, observation):
        '''Tell 5s to a random player if it has them'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_fives(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the tell_five hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_randomly(agent, observation):
        '''Tell to a random player a random information prioritizing color'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_randomly(observation)
            assert (destination_name, value, type) != (None, None, None)
            print(">>>give the random hint ", type, " ", value, " to ", destination_name)
            return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    ###############
    # DISCARD RULES
    ###############

    @staticmethod
    def discard_useless_card(agent, observation, lowest=False):
        """
        Discards a useless card, if possible
        @param agent: the player that will try to discard
        @param observation: current state of the game
        @param lowest: if True, the lowest useless card will be discarded
        @return: a request to discard the useless card, None if it is not possible
        """
        if observation['usedNoteTokens'] != 0:
            card_pos = agent.card_discard_manager.discard_useless_card(observation, lowest)
            if card_pos is not None:
                print(">>>discard useless card:", card_pos)
                return GameData.ClientPlayerDiscardCardRequest(agent.name, card_pos)
        return None

    @staticmethod
    def discard_duplicate_card(agent, observation):
        """
        Discards a duplicate card, if possible
        @param agent: the player that will try to discard
        @param observation: current state of the game
        @return: a request to discard the duplicate card, None if it is not possible
        """
        if observation['usedNoteTokens'] != 0:
            card_pos = agent.card_discard_manager.discard_duplicate_card(observation)
            if card_pos is not None:
                print(">>>discard duplicate card:", card_pos)
                return GameData.ClientPlayerDiscardCardRequest(agent.name, card_pos)
        return None

    @staticmethod
    def discard_less_relevant(agent, observation):
        """
        Discards the less relevant card of the hand, if possible
        @param agent: the player that will try to discard
        @param observation: current state of the game
        @return: a request to discard the less relevant card, None if it is not possible
        """
        if observation['usedNoteTokens'] != 0:
            card_pos = agent.card_discard_manager.discard_less_relevant(observation)
            print(">>>discard less relevant card:", card_pos)
            return GameData.ClientPlayerDiscardCardRequest(agent.name, card_pos)
        return None

    @staticmethod
    def discard_randomly(agent, observation):
        """
        Discards a random card, if possible
        @param agent: the player that will try to discard
        @param observation: current state of the game
        @return: a request to discard the random card, None if it is not possible
        """
        if observation['usedNoteTokens'] != 0:
            card_pos = agent.card_discard_manager.discard_randomly(observation)
            print(">>>discard random card:", card_pos)
            return GameData.ClientPlayerDiscardCardRequest(agent.name, card_pos)
        return None

    @staticmethod
    def discard_oldest(agent, observation):
        """
        Discards the oldest card, if possible
        @param agent: the player that will try to discard
        @param observation: current state of the game
        @return: a request to discard the oldest card, None if it is not possible
        """
        if observation['usedNoteTokens'] != 0:
            card_pos = agent.card_discard_manager.discard_oldest(observation)
            print(">>>discard oldest card:", card_pos)
            return GameData.ClientPlayerDiscardCardRequest(agent.name, card_pos)
        return None
