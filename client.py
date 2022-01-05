#!/usr/bin/env python3

from sys import stdout
from threading import Thread
import GameData
import socket
import os
import time
import cmd
import argparse

from constants import *
from agent import Agent

# Arguments management

parser = argparse.ArgumentParser()
parser.add_argument('--ip', type=str, default=HOST, help='IP address of the host')
parser.add_argument('--port', type=int, default=PORT, help='Port of the server')
parser.add_argument('--player_name', type=str, help='Player name')
parser.add_argument('--ai_player', help='Play with the AI agent', action='store_true')
args = parser.parse_args()

ip = args.ip
port = args.port

if args.ai_player is not None:
    playerName = 'AI'
    agent = Agent(playerName)

else:
    if args.player_name is None:
        print("You need the player name to start the game, or play with the AI by specifying '--ai_player'.")
        exit(-1)
    else:
        playerName = args.player_name

run = True
statuses = ["Lobby", "Game", "GameHint"]
status = statuses[0]
hintState = ("", "")
wait_move = 1
observation = []


def agentPlay():
    global run
    global status
    while run:
        if status == statuses[0]:
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        # wait to feel more human
        time.sleep(wait_move)
        # Get observation
        # ask to show the data to the server - should be the "obs"
        request = GameData.ClientGetGameStateRequest(playerName)
        s.send(request.serialize())
        # should wait to get the updated observation
        # Compute action and send to server
        # action = agent.simple_heuristic_choice(observation)
        action = agent.dummy_agent_choice(observation)
        s.send(action)

        # leave replay lobby when game has ended
        # if self.game_ended:
            # self.ws.send(cmd.gameUnattend())
            # self.game_ended = False
            # self.gameHasStarted = False

    time.sleep(1)


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
    time.sleep(6)

    # 4) Communicate to the server that you are ready
    print("I am ready to start the game.")
    request = GameData.ClientPlayerStartRequest(playerName)
    s.send(request.serialize())

    if type(playerName) == Agent:
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
            players = data.players

        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            print("Game start! My team mates are: ", players)

            # 7) The game can finally start
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())

            # 8) Set the status from lobby to game.
            status = statuses[1]
            print("---Starting game process done----")

        if type(data) is GameData.ServerGameStateData:
            dataOk = True
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

            # should implement the return observation here
            observation = {
                'current_player': data.currentPlayer,  # should return the player name
                'current_player_offset': 0,
                'usedStormTokens': data.usedStormTokens,
                'usedNoteTokens': data.usedNoteTokens,
                'players': data.players,
                'num_players': data.players.size,
                # 'deck_size': self.deck_size,
                # 'fireworks': self.fireworks,
                # 'legal_moves': self.get_legal_moves(),
                # 'observed_hands': self.get_observed_hands(),  # moves own hand to front
                'discard_pile': data.discard_pile,
                # 'card_knowledge': self.get_card_knowledge(),
                # 'last_moves': self.last_moves,  # actually not contained in the returned dict of the

                'tableCards': data.tableCards,
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

        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")

        if type(data) is GameData.ServerHintData:
            dataOk = True
            print("Hint type: " + data.type)
            print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t" + str(i))

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
