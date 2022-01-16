from agent import Agent
import GameData
import random

class Ruleset():

###############
## PLAY RULES
###############

    @staticmethod 
    def get_best_play(agent: Agent, observation):
        ################
        #  Do we need to add some checks (?) don't think so
        ################
        card_pos = agent.get_best_play(observation)

        if card_pos is not None:
            print(">>>play the card number:", card_pos)
            return GameData.ClientPlayerPlayCardRequest(agent.name, card_pos)
        return None

###############
## HINT RULES
###############

    @staticmethod 
    def get_best_hint(agent: Agent, observation):
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.get_hint(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the helpful hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod 
    def get_low_value_hint(agent: Agent, observation):
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.get_low_value_hint(observation)
            print(">>>give the low_value hint ", type, " ", value, " to ", destination_name)
            return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_randomly(agent: Agent, observation):
        '''Tell to a random player a random information prioritizing color'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_randomly(observation)
            print(">>>give the low_value hint ", type, " ", value, " to ", destination_name)
            return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_fives(agent: Agent, observation):
        '''Tell 5s to a random player if it has them'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_fives(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the helpful hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_ones(agent: Agent, observation):
        '''Tell 1s to a random player if it has them'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_ones(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the helpful hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    # Prioritize color, just next player is considered
    @staticmethod
    def tell_unknown(agent: Agent, observation):
        '''Tell a random player an unknown information prioritizing color'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_unknown(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the helpful hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

    @staticmethod
    def tell_anyone_useless_card(agent: Agent, observation):
        pass

    @staticmethod
    def tell_most_information(agent: Agent, observation):
        '''Tell 1s to a random player if it has them'''
        if observation['usedNoteTokens'] < 8:
            destination_name, value, type = agent.card_hints_manager.tell_most_information(observation)
            if (destination_name, value, type) != (None, None, None):  # found a best hint
                print(">>>give the helpful hint ", type, " ", value, " to ", destination_name)
                return GameData.ClientHintData(agent.name, destination_name, type, value)
        return None

###############
## DISCARD RULES
###############

    @staticmethod 
    def get_best_discard(agent: Agent, observation):
        if observation['usedNoteTokens'] != 0:
            card_pos, _, _ = agent.get_best_discard(observation)
            print(">>>discard the card number:", card_pos)
            return GameData.ClientPlayerDiscardCardRequest(agent.name, card_pos)
        return None


    @staticmethod
    def discard_duplicate_card(agent: Agent, observation):
        '''
        Discard a card that I see in some other player's hand
        '''
        if observation['usedNoteTokens'] != 0:
            cards_in_player_hands = agent.counterOfCards()
            for player_info in observation['players']:
                if (player_info.name != agent.name):
                    cards_in_player_hands += agent.counterOfCards(player_info.hand)

            for (card_pos, p) in enumerate(agent.possibilities):
                # for each possible value of the card I check that Its already in someone hand
                if all(cards_in_player_hands[c]!=0 for c in p):
                    # this card is surely a duplicate
                    return GameData.ClientPlayerDiscardCardRequest(agent.name, card_pos)
            else:
                return None
        return None
    




