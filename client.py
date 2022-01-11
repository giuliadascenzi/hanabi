#!/usr/bin/env python3

from sys import stdout
from threading import Thread
import GameData
import socket
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
hintState = []
wait_move = 7
observation = {'current_player': None,
               'usedStormTokens': 0,
               'usedNoteTokens': 0,
               'players': None,
               'num_players': 0,
               # 'deck_size': self.deck_size,
               # 'fireworks': self.fireworks,
               # 'legal_moves': self.get_legal_moves(),
               'discard_pile': None,
               # 'card_knowledge': self.get_card_knowledge(),
               # 'last_moves': self.last_moves,  # actually not contained in the returned dict of the
               'tableCards': None
               }


def agentPlay():
    global run
    global status
    global doitOnce
    while run:
        if status == statuses[0] and doitOnce:  # Lobby
            print("I am ready to start the game.")
            doitOnce = False
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        if status == statuses[1]:
            # Get observation : ask to show the data to the server
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            # Compute action and send to server
            if observation['current_player'] == playerName:
                # action = agent.dummy_agent_choice(observation)
                action = agent.simple_heuristic_choice(observation, hintState)
                s.send(action.serialize())


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

    # 3) Wait until all the players entered in the lobby -> sleep some seconds
    # TODO: (This is an andrea suggestion)
    # time.sleep(6)

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
            print("Game start!")

            # 7) The game can finally start
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())

            # 8) Set the status from lobby to game.
            status = statuses[1]
            print("---Starting game process done----")

        if type(data) is GameData.ServerGameStateData:
            dataOk = True

            if playerName != "AI":
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
                    print("Taking care of the hints")
                    hintState.remove(hint)
                    print("Hints left :", hintState)

        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")

        if type(data) is GameData.ServerHintData:
            dataOk = True
            print("Hint type: " + data.type)
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
                if not notedHint:
                    notedHint = True
                    if data.type == 'value':
                        hintState.append({'player': data.destination, 'value': d_val, 'color': None, 'card_index': i})
                    else:
                        hintState.append({'player': data.destination, 'value': None, 'color': d_col, 'card_index': i})

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
