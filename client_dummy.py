#!/usr/bin/env python3

from sys import argv, stdout
from threading import Thread
import GameData
import socket
from constants import *
import os
import time
import random

run = True

AI_type= "dummy"

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

players = []

playerName = ""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

playerTurn = ""
playerHands = ""
tableCards = ""
discardPile = ""
usedNoteTokens = ""
usedStormTokens= ""


def start_game():
    global run
    global status
    global AI_type
    global players
    global playerName

    # Check of the arguments
    if len(argv) < 4:
        print("You need the player name to start the game.")
        #exit(-1)
        playerName = AI_type
        ip = HOST
        port = PORT
    else:
        playerName = argv[3]
        ip = argv[1]
        port = int(argv[2])

    # 0) open the connection
    s.connect((ip, port))

    # 1) request a connection from the server
    print("Trying to estabilisy a connection with the server...")
    request = GameData.ClientPlayerAddData(playerName)
    s.send(request.serialize())

    # 2) wait the response of the server
    data = s.recv(DATASIZE) # blocking till it does not get it
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print(data.message)
    
    # 3) Wait until all the players entered in the lobby -> sleep some seconds TODO: (This is an andrea suggestion)
    time.sleep(6)

    # 4) Comunicate to the server that you are ready
    print("I am ready to start the game.")
    request = GameData.ClientPlayerStartRequest(playerName)
    s.send(request.serialize())

    # 5) Wait the response from the server
    data = s.recv(DATASIZE) # blocking till it does not get it
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerStartRequestAccepted:
        print("Ready: " + str(data.acceptedStartRequests) + "/"  + str(data.connectedPlayers) + " players")

    # 6) Wait until everyone is ready and the game can start.     
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    players = data.players
    if type(data) is GameData.ServerStartGameData:
        print("Game start!")
        print("My team mates are: ", players)

    # 7) The game can finally start
    s.send(GameData.ClientPlayerReadyData(playerName).serialize())

    # 8) Set the status from lobby to game.
    status = statuses[1]

    print("---Starting game process done----")
    return

def show():
    global playerTurn 
    global playerHands
    global tableCards 
    global discardPile 
    global usedNoteTokens 
    global usedStormTokens
    # ask to show the data to the server
    request = GameData.ClientGetGameStateRequest(playerName)
    s.send(request.serialize())
    # wait the response
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerGameStateData:
        playerTurn = data.currentPlayer
        playerHands = data.players
        tableCards = data.tableCards
        discardPile =data.discardPile
        usedNoteTokens = data.usedNoteTokens
        usedStormTokens= data.usedStormTokens

        print("Current player: " + playerTurn)
        print("Player hands: ")
        for p in playerHands:
            print(p.toClientString())
        print("Table cards: ")
        for pos in tableCards:
            print(pos + ": [ ")
            for c in data.tableCards[pos]:
                print(c.toClientString() + " ")
            print("]")
        print("Discard pile: ")
        for c in discardPile :
            print("\t" + c.toClientString())  
        print("Note tokens used: " + str(usedNoteTokens) + "/8")
        print("Storm tokens used: " + str(usedStormTokens) + "/3")
    return

def dummy_agent_choice():
    
    if usedNoteTokens < 3 and random.randint(0,2) == 0:
        # give random hint to the next player
        next_player_index = (players.index(playerName)+1) % len(players)
        destination = players[next_player_index]
        card = random.choice([card for card in playerHands[next_player_index].hand if card is not None])
        
        if random.randint(0,1) == 0:
            type= "color"
            value = card.color
        else:
            type=  "value"
            value = card.value
        
        print(">>>give some random hint")
        return GameData.ClientHintData(playerName, destination, type, value)
        
    elif random.randint(0,1) == 0:
        # play random card
        card_pos = random.choice([0,1,2,3,4])
        print(">>>play some random card")
        return GameData.ClientPlayerPlayCardRequest(playerName, card_pos)
    
    else:
        # discard random card
        card_pos = random.choice([0,1,2,3,4])
        print(">>>discard some random card")
        return GameData.ClientPlayerDiscardCardRequest(playerName, card_pos)


# ------------- MAIN -------------

start_game()
show()
while run: # while the game is going
    if (playerTurn!=playerName): # while is not my turn
        data = s.recv(DATASIZE)
        if not data:
            continue
        data = GameData.GameData.deserialize(data)
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
        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            run = False
        print("End of a turn")
        show()
    else:
        # Its the player turn
        print("ITS MY TURN")
        #request= GameData.ClientPlayerPlayCardRequest(playerName, int(1))
        request = dummy_agent_choice()
        s.send(request.serialize())
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        print(data.action)
        show()


print("FINEEEE")       
os._exit(0)

