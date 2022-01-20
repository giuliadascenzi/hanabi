#!/usr/bin/env python3

from sys import stdout
from threading import Thread
import GameData
import socket
import time
import os
import argparse
import matplotlib.pyplot as plt
import numpy as np

from constants import *
from agent import Agent, Knowledge
from ruleset import Ruleset

# Arguments management
parser = argparse.ArgumentParser()
parser.add_argument('--ip', type=str, default=HOST, help='IP address of the host')
parser.add_argument('--port', type=int, default=PORT, help='Port of the server')
player = parser.add_mutually_exclusive_group()
player.add_argument('--player-name', type=str, help='Player name')
player.add_argument('--ai-player', type=str, help='Play with the AI agent and give him a name')
args = parser.parse_args()

ip = args.ip
port = args.port
AI = False
agent = None
playerName = ""

if args.ai_player is not None:
    playerName = args.ai_player
    AI = True
else:
    if args.player_name is None:
        print("You need the player name to start the game, or play with the AI by specifying '--ai-player'.")
        exit(-1)
    else:
        playerName = args.player_name

num_cards = ""
run = True
first = True
statuses = ["Lobby", "Game", "GameHint"]
status = statuses[0]
observation = {'players': None,
               'current_player': None,
               'usedStormTokens': 0,
               'usedNoteTokens': 0,
               'fireworks': None,
               'discard_pile': None,
               'playersKnowledge': []
               }
scores = []
player_names = []
ruleset = Ruleset()


def agentPlay():
    global run
    global status
    global observation
    global first

    if status == statuses[0]:  # Lobby
        print("I am ready to start the game.")
        s.send(GameData.ClientPlayerStartRequest(playerName).serialize())

    while run:
        if status == statuses[1]:
            if observation['current_player'] == playerName:
                print("[" + playerName + " - " + status + "]: ", end="")
                # action = agent.dummy_agent_choice(observation)
                # action = agent.simple_heuristic_choice(observation)
                action = agent.rl_choice(observation)
                # action = agent.osawa_outer_choice(observation)
                # action = agent.pier_choice(observation)
                # action = agent.vanDerBergh_choice(observation)
                #action = agent.vanDerBergh_choice_prob(observation)
                #action = agent.rule_choice(observation)
                # action = agent.rule_choice_delta(observation)
                try:
                    s.send(action.serialize())
                except:
                    print("Error")
                    run = False
                observation['current_player'] = ""
        # time.sleep(5)


def next_turn():
    # Get observation : ask to the server to show the data
    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())


def manageInput():
    global run
    global status
    while run:
        print("[" + playerName + " - " + status + "]: ", end="")
        command = input()
        # Choose data to send
        if command == "exit":
            run = False
            os._exit(0)
        elif command == "ready" and status == statuses[0]:
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        elif command == "show" and status == statuses[1]:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        elif command.split(" ")[0] == "discard" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerDiscardCardRequest(playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'discard <num>'?")
                continue
        elif command.split(" ")[0] == "play" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerPlayCardRequest(playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'play <num>'?")
                continue
        elif command.split(" ")[0] == "hint" and status == statuses[1]:
            try:
                destination = command.split(" ")[2]
                t = command.split(" ")[1].lower()
                if t != "colour" and t != "color" and t != "value":
                    print("Error: type can be 'color' or 'value'")
                    continue
                value = command.split(" ")[3].lower()
                if t == "value":
                    value = int(value)
                    if int(value) > 5 or int(value) < 1:
                        print("Error: card values can range from 1 to 5")
                        continue
                else:
                    if value not in ["green", "red", "blue", "yellow", "white"]:
                        print("Error: card color can only be green, red, blue, yellow or white")
                        continue
                s.send(GameData.ClientHintData(playerName, destination, t, value).serialize())
            except:
                print("Maybe you wanted to type 'hint <type> <destinatary> <value>'?")
                continue
        elif command == "":
            print("[" + playerName + " - " + status + "]: ", end="")
        else:
            print("Unknown command: " + command)
            continue
        stdout.flush()


def initialize(players):
    global agent
    global num_cards

    if len(players) < 4:
        num_cards = 5
    else:
        num_cards = 4

    if AI:
        agent = Agent(playerName, players.index(playerName), num_cards, ruleset)

    playersKnowledge = {name: [Knowledge(color=None, value=None) for j in range(num_cards)] for name in players}

    return playersKnowledge


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # 0) open the connection
    s.connect((ip, port))

    # 1) request a connection from the server
    print("Trying to establish a connection with the server...")
    request = GameData.ClientPlayerAddData(playerName)
    s.send(request.serialize())

    # 2) wait the response of the server
    try:
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
    except:
        print("Error")
        run = False
        data = ""

    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
    print("[" + playerName + " - " + status + "]: ", end="")

    if AI:
        Thread(target=agentPlay).start()
    else:
        Thread(target=manageInput).start()

    while run:
        dataOk = False

        # 5) Wait the response from the server
        try:
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
        except:
            print("Error")
            run = False
        if not data:
            continue
       
        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True

            # 6) Wait until everyone is ready and the game can start.
            # data = s.recv(DATASIZE)
            # data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            player_names = data.players
            playersKnowledge = initialize(data.players)
            print("Game start!")
            if AI: next_turn()

            # 7) The game can finally start
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())

            # 8) Set the status from lobby to game.
            #status = statuses[1]
            
            print("---Starting game process done----")

        if type(data) is GameData.ServerGameStateData:
            dataOk = True

            if not AI:
                print("Current player: " + data.currentPlayer)
                print("Player hands: ")
                for p in data.players:
                    print(p.toClientString())
                print("Table cards: ")
                for pos in data.tableCards:
                    print(pos + ": [ ")
                    for c in data.tableCards[pos]:
                        print(c.toClientString() + " ")
                    print("]")
                print("Discard pile: ")
                for c in data.discardPile:
                    print("\t" + c.toClientString())
                print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
                print("Storm tokens used: " + str(data.usedStormTokens) + "/3")

            else:
                observation = {'players': data.players,
                               'current_player': data.currentPlayer,
                               'usedStormTokens': data.usedStormTokens,
                               'usedNoteTokens': data.usedNoteTokens,
                               'fireworks': data.tableCards,
                               'discard_pile': data.discardPile,
                               'playersKnowledge': playersKnowledge}
                
            if AI and first:
                # 8) Set the status from lobby to game.
                status = statuses[1]
                agent.set_players(observation)
                first = False    

        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)

        if type(data) is GameData.ServerActionValid:  # DISCARD 
            dataOk = True
            print(" [", data.lastPlayer, "] :", data.action, data.card.toString())
            # update players knowledge
            playersKnowledge[data.lastPlayer].pop(data.cardHandIndex)
            if data.handLength == num_cards:  # if the player got a new card
                playersKnowledge[data.lastPlayer].append(Knowledge(None, None))
            # if the player was the agent update its internal possibilities
            if AI and data.lastPlayer == playerName:
                agent.reset_possibilities(data.cardHandIndex, data.handLength == num_cards)
            if AI: next_turn()

        if type(data) is GameData.ServerPlayerMoveOk:
            dataOk = True
            print("[", data.lastPlayer, "] :", data.action, data.card.toString())
            # update players knowledge
            playersKnowledge[data.lastPlayer].pop(data.cardHandIndex)
            if data.handLength == num_cards:  # if the player got a new card
                playersKnowledge[data.lastPlayer].append(Knowledge(None, None))
            # if the player was the agent update its internal possibilities
            if AI and data.lastPlayer == playerName:
                agent.reset_possibilities(data.cardHandIndex, data.handLength == num_cards)

            if AI: next_turn()

        if type(data) is GameData.ServerPlayerThunderStrike:  # PLAYED WRONG
            dataOk = True
            print("[", data.lastPlayer, "] :", data.action, data.card.toString())
            # update players knowledge
            playersKnowledge[data.lastPlayer].pop(data.cardHandIndex)
            if data.handLength == num_cards:  # if the player got a new card
                playersKnowledge[data.lastPlayer].append(Knowledge(None, None))
            # if the player was the agent update its internal possibilities
            if AI and data.lastPlayer == playerName:
                agent.reset_possibilities(data.cardHandIndex, data.handLength == num_cards)

            if AI: next_turn()

        if type(data) is GameData.ServerHintData:  # HINT
            dataOk = True
            print("[" + data.source + "]: " + "Hinted to " + data.destination + " cards with value/color " + str(
                data.value) + " are: ", data.positions)
            d_val = d_col = None
            if data.type == 'value':
                d_val = data.value
            else:
                d_col = data.value
            for i in data.positions:     
                if d_val is not None:
                    playersKnowledge[data.destination][i].value = d_val
                if d_col is not None:
                    playersKnowledge[data.destination][i].color = d_col

            if AI and data.destination == playerName:
                agent.receive_hint(data.destination, data.type, data.value, data.positions)

            if AI: next_turn()

        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)

        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            scores.append(data.score)
            avg = sum(scores) / len(scores)
            print(" |Average score so far:  ", avg)
            print(" |Games played: ", len(scores))
            print(" |Best result: ", max(scores))
            print(" |Worst result: ", min(scores))
            if len(scores) >= 100:
                x = np.arange(0, len(scores), 1)
                plt.plot(x, scores)
                plt.plot(x, [avg] * len(scores), 'r--')  # plotting the average
                plt.scatter(x, scores)
                plt.xlabel('games')
                plt.ylabel('scores')
                plt.xticks(x)
                plt.yticks(scores)
                plt.title('Agent =vanDerBergh_choice Num_players = 2')
                t = time.localtime()
                timestamp = time.strftime('%b-%d-%Y_%H%M', t)
                plt.savefig('graphs/' + timestamp + '.png')
                run = False
            '''
            if len(scores) % 10 == 0:
                ruleset.fitness( sum(scores[-10:]) / 10 )
                ruleset.shuffle_rules()
            '''
            # reset and re-initialize

            if run is not False:
                del agent
                observation = {'players': None,
                               'current_player': None,
                               'usedStormTokens': 0,
                               'usedNoteTokens': 0,
                               'fireworks': None,
                               'discard_pile': None,
                               'playersKnowledge': []}
                #time.sleep(5)
                status = statuses[0]
                first = True
                playersKnowledge = initialize(player_names)
                if AI: next_turn()
                stdout.flush()
                # run = False
                print("Ready for a new game")

        if not dataOk:
            print("Unknown or unimplemented data type: " + str(type(data)))

        if not AI:
            print("[" + playerName + " - " + status + "]: ", end="")
        stdout.flush()

    print("END")
