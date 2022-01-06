#!/usr/bin/env python3

from sys import argv, stdout
from threading import Thread
from Agents.DummyAgent import DummyAgent
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

playerName = ""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

playerTurn = ""
playing_agent = ""



def start_game():
    global run
    global status
    global AI_type


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
    players_names = data.players
    if type(data) is GameData.ServerStartGameData:
        print("Game start!")
        print("My team mates are: ", players_names)

    # 7) The game can finally start
    s.send(GameData.ClientPlayerReadyData(playerName).serialize())

    # 8) Set the status from lobby to game.
    status = statuses[1]

    print("---Starting game process done----")
    return playerName, players_names

def show():
    # ask to show the data to the server
    request = GameData.ClientGetGameStateRequest(playerName)
    s.send(request.serialize())
    # wait the response
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerGameStateData:
        print("Current player: " + playerTurn)
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
        for c in data.discardPile :
            print("\t" + c.toClientString())  
        print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
        print("Storm tokens used: " + str(data.usedStormTokens) + "/3")
    return


def init_data(playerName, players_names):
    global playing_agent
    global playerTurn

    
    playing_agent = DummyAgent(playerName)
    
    # ask to show the data to the server
    request = GameData.ClientGetGameStateRequest(playerName)
    s.send(request.serialize())
    # wait the response
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerGameStateData:
        playerTurn = data.currentPlayer
        playersInfo = data.players
        tableCards = data.tableCards
        discardPile = data.discardPile
        usedNoteTokens = data.usedNoteTokens # = 0
        usedStormTokens= data.usedStormTokens # = 0
    
    print("##################", data.players)
    playing_agent.initialize(num_players= len(players_names), players_names= players_names, k=len(playersInfo[0].hand), board= tableCards, players_info= playersInfo, discard_pile=discardPile)

def update_data():
    global playing_agent
    global playerTurn

    # ask to show the data to the server
    request = GameData.ClientGetGameStateRequest(playerName)
    s.send(request.serialize())
    # wait the response
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerGameStateData:
        playerTurn = data.currentPlayer
        playersInfo = data.players
        tableCards = data.tableCards
        discardPile = data.discardPile
        usedNoteTokens = data.usedNoteTokens 
        usedStormTokens= data.usedStormTokens 
    

    playing_agent.update(board= tableCards, players_info= playersInfo, discardPile=discardPile, usedNoteTokens=usedNoteTokens, usedStormTokens=usedStormTokens )



# ------------- MAIN -------------

def main():
    global playing_agent
    global playerTurn
    global run
    global status
    global AI_type

    playerName, players_names = start_game()
    init_data(playerName, players_names)
    while run: # while the game is going
        time.sleep(5)
        print("***********************")
        show()
        print("***********************")
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
            
        else:
            # Its the player turn
            print("ITS MY TURN")
            print("[" + playerName + " - " + status + "]: ", end="")
            request = playing_agent.get_turn_action()
            s.send(request.serialize())
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
            print(data.action)
        
        update_data()


    print("FINEEEE")       
    os._exit(0)

main()

