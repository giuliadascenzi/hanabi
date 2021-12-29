#!/usr/bin/env python3

from sys import argv, stdout
from threading import Thread
import GameData
import socket
from constants import *
import os
import time

run = True

AI_type= "dummy"

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

players = []

playerName = ""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


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
    players = data.pleyers
    if type(data) is GameData.ServerStartGameData:
        print("Game start!")
        print("My team mates are: ", players)

    # 7) The game can finally start
    s.send(GameData.ClientPlayerReadyData(playerName).serialize())

    # 8) Set the status from lobby to game.
    status = statuses[1]

    print("---Starting game process done----")
    return
    
start_game()
print("time to sleep")
time.sleep(5)
print("My work is done")
os._exit(0)