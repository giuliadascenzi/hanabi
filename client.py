#!/usr/bin/env python3

from sys import stdout
from threading import Thread
import GameData
import socket
import time
import os
import argparse

from constants import *
from agent import Agent

# Arguments management

parser = argparse.ArgumentParser()
parser.add_argument('--ip', type=str, default=HOST, help='IP address of the host')
parser.add_argument('--port', type=int, default=PORT, help='Port of the server')
player = parser.add_mutually_exclusive_group()
player.add_argument('--player-name', type=str, help='Player name')
player.add_argument('--ai-player', type=str, help='Play with the AI agent')
args = parser.parse_args()

ip = args.ip
port = args.port
agent = ""
playerName = ""

if args.ai_player is not None:
    playerName = args.ai_player
    agent = Agent(playerName)

else:
    if args.player_name is None:
        print("You need the player name to start the game, or play with the AI by specifying '--ai-player'.")
        exit(-1)
    else:
        playerName = args.player_name

run = True
statuses = ["Lobby", "Game", "GameHint"]
status = statuses[0]
doitOnce = True
players = []
rankHintedButNoPlay = None
hintState = []
playersKnowledge = []
wait_move = 7
observation = {'current_player': None,
               'usedStormTokens': 0,
               'usedNoteTokens': 0,
               'players': None,
               'num_players': 0,
               # 'deck_size': self.deck_size,
               'fireworks': None,
               # 'legal_moves': self.get_legal_moves(),
               'discard_pile': None,
               # 'card_knowledge': self.get_card_knowledge(),
               # 'last_moves': self.last_moves,  # actually not contained in the returned dict of the
               'hints': hintState,
               'playersKnowledge': playersKnowledge,
               'rankHintedButNoPlay': rankHintedButNoPlay
               }


def agentPlay():
    global run
    global status
    global doitOnce
    global turn
    while run:
        if status == statuses[0] and doitOnce:  # Lobby
            print("I am ready to start the game.")
            doitOnce = False
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        if status == statuses[1]:
            # Get observation : ask to show the data to the server
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            time.sleep(5)
            # Compute action and send to server
            if observation['current_player'] == playerName:
                print("I am the current player (", playerName, ") and I will play now")
                # action = agent.dummy_agent_choice(observation)
                action = agent.simple_heuristic_choice(observation)
                print("My action is: ", action)
                s.send(action.serialize())
                time.sleep(10)


def manageInput():
    global run
    global status
    while run:
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


## --- MAIN ---

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # 0) open the connection
    s.connect((ip, port))

    # 1) request a connection from the server
    print("Trying to establish a connection with the server...")
    request = GameData.ClientPlayerAddData(playerName)
    s.send(request.serialize())

    # 2) wait the response of the server
    data = s.recv(DATASIZE)  # blocking till it does not get it
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
    print("[" + playerName + " - " + status + "]: ", end="")

    if type(agent) == Agent:
        Thread(target=agentPlay).start()
    else:
        Thread(target=manageInput).start()

    while run:
        dataOk = False

        # 5) Wait the response from the server
        data = s.recv(DATASIZE)
        if not data:
            continue
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            print("Ready: " + str(data.acceptedStartRequests) + "/" + str(data.connectedPlayers) + " players")

            # 6) Wait until everyone is ready and the game can start.
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
            # players = data.players

        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            players = data.players
            for p in players:
                playersKnowledge.append({'player': p.name, 'knowledge': []})

            if players < 4:
                num_cards = 5
            else:
                num_cards = 4
            rankHintedButNoPlay = [0] * players
            for i in range(len(rankHintedButNoPlay)):
                rankHintedButNoPlay[i] = [False] * num_cards

            print("Game start!")

            # 7) The game can finally start
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())

            # 8) Set the status from lobby to game.
            status = statuses[1]
            print("---Starting game process done----")

        if type(data) is GameData.ServerGameStateData:
            dataOk = True

            if args.ai_player is None:
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
                print("Hints: ")
                for h in hintState:
                    print(h)
                print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
                print("Storm tokens used: " + str(data.usedStormTokens) + "/3")

            else:
                observation = {
                    'current_player': data.currentPlayer,  # should return the player name
                    'usedStormTokens': data.usedStormTokens,
                    'usedNoteTokens': data.usedNoteTokens,
                    'players': data.players,
                    'num_players': len(data.players),
                    # 'deck_size': self.deck_size,
                    'fireworks': data.tableCards,
                    # 'legal_moves': self.get_legal_moves(),
                    'discard_pile': data.discardPile,
                    'hints': hintState,
                    'playersKnowledge': playersKnowledge,
                    'rankHintedButNoPlay': rankHintedButNoPlay
                    # 'last_moves': self.last_moves,  # actually not contained in the returned dict of the
                }

                # legal_moves_as_int, legal_moves_as_int_formated = self.get_legal_moves_as_int(observation['legal_moves'])
                # observation["legal_moves_as_int"] = legal_moves_as_int
                # observation["legal_moves_as_int_formated"] = legal_moves_as_int_formated
                # observation['vectorized'] = self.get_vectorized(observation)

        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)

        if type(data) is GameData.ServerActionValid:
            dataOk = True
            print("Action valid!")
            print("Current player: " + data.player)

        if type(data) is GameData.ServerPlayerMoveOk:
            dataOk = True
            print("Nice move!")
            print("Current player: " + data.player)
            for hint in hintState:
                if hint['player'] == data.lastPlayer and hint['card_index'] == data.cardHandIndex:
                    hintState.remove(hint)
            for p in playersKnowledge:
                if p['player'] == data.lastPlayer:
                    for k in p['knowledge']:
                        if k[0] == data.cardHandIndex:
                            p['knowledge'].remove(k)

        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")
            print("Current player: " + data.player)

        if type(data) is GameData.ServerHintData:
            dataOk = True
            print("Hint type: " + data.type)
            d_val = d_col = None
            if data.type == 'value':
                d_val = data.value
            else:
                d_col = data.value
            print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t" + str(i))

                notedHint = False
                for hint in hintState:
                    if hint['player'] == data.destination and hint['card_index'] == i:
                        notedHint = True
                        if data.type == 'value':
                            hint['value'] = d_val
                        else:
                            hint['color'] = d_col
                        break
                if not notedHint:
                    notedHint = True
                    hintState.append({'player': data.destination, 'value': d_val, 'color': d_col, 'card_index': i})

                notedKnowledge = False
                for p in playersKnowledge:
                    if p['player'] == data.destination:
                        for k in p['knowledge']:
                            if k[0] == i:
                                notedKnowledge = True
                                if data.type == 'value':
                                    k[1] = d_val
                                else:
                                    k[2] = d_col
                        if not notedKnowledge:
                            p['knowledge'].append((i, d_val, d_col))
                if not notedKnowledge:
                    playersKnowledge.append({'player': data.destination, 'knowledge': [(i, d_val, d_col)]})
            print("Current player: " + data.player)

        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)

        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            run = False

        if not dataOk:
            print("Unknown or unimplemented data type: " + str(type(data)))
        print("[" + playerName + " - " + status + "]: ", end="")
        stdout.flush()
