import dds
import GenDeal as gd
from Agent import Agent, STAT_SIZE
from Dummy import Dummy
from Helper import unclash, toString, calcScore
from Bidding import POSSIBLE_BID_COUNT, possible_bids

from keras.models import Sequential, load_model
from keras.layers import Dense
from keras import regularizers, optimizers
import numpy as np
import tensorflow as tf
from keras import backend as K

import os
import json

LAYER0 = 128
LAYER1 = 128
LAYER2 = 128
LAYER3 = 128
LAYER4 = 128
L2_REGULARIZER = 0.01
BIDDING_ALPHA = 0.1
EXPLORE_COEFFICIENT = 0.001

_DEBUG = 3


# def _loss ():
def custom_loss (y_pred, y_true):
	y_pred = tf.convert_to_tensor (y_pred)
	y_true = tf.convert_to_tensor (y_true)
	cross_entropy_loss = - 1 * K.sum (y_pred * K.log (y_true), 1)
	# print (cross_entropy_loss)
	return cross_entropy_loss
	# return custom_loss

def saveNetwork (model, filename):
	model.save (filename)
	return

def loadNetwork (filename = ""):
	if filename == "":
		model = Sequential ()
		model.add (Dense (LAYER0, input_shape = (220,))) #52 + (SHDC + AKOJT9s + AKs = 4 + 6 + 8) * 3 + 38 * 3
		model.add (Dense (LAYER1, activation = 'sigmoid', kernel_regularizer = regularizers.l2(L2_REGULARIZER)))
		model.add (Dense (LAYER2, activation = 'sigmoid', kernel_regularizer = regularizers.l2(L2_REGULARIZER)))
		model.add (Dense (LAYER3, activation = 'sigmoid', kernel_regularizer = regularizers.l2(L2_REGULARIZER)))
		model.add (Dense (LAYER4, activation = 'sigmoid', kernel_regularizer = regularizers.l2(L2_REGULARIZER)))
		model.add (Dense (38, activation = 'sigmoid'))
		sgd = optimizers.SGD (lr = 0.01)
		model.compile (loss = 'mse', optimizer = sgd)
		return model

	model = load_model (filename, custom_objects={'custom_loss': _loss()})
	return model

def play (agents):
	bids = []
	player = 0
	stats = list (-1 for i in range (STAT_SIZE * 4))
	passes = ["P","P","P"]
	while True:
		agent = agents [player]
		state = (stats, bids, player)
		bid = agent.move (state)
		bids.append (bid)
		if toString (bids) in agent.biddingBase().keys ():
			for i in range (STAT_SIZE):
				stats [player * STAT_SIZE + i] = agent.biddingBase()[toString(bids)][i]
		agent.updateStat (bids)
		player += 1
		if player == 4:
			player = 0
		if bids [-3:] == passes:
			break
	return bids

def loadBiddingBase (filename = ""):
	
	system = {}

	if filename == "":
		return system

	if os.path.getsize (filename) == 0:
		return system

	file = open (filename, "r")
	try:
		system = dict (json.loads (file.read ()))
	except:
		print ("Parsing Error")
		print ("")
	file.close ()

	return system

def writeBiddingBase (system, filename):

	# import os.path
	# from pathlib import Path

	# if Path (filename).is_file() and not overwrite:
	# 	print ("Cannot Overwrite System")
	# 	return

	file = open (filename, "w")
	file.write (json.dumps (system))
	file.close ()

def giveHands (agents, hands):
	
	for i in range (4):
		agents [i].setHand (hands [i])

def setTarget (outputHistory, moveHistory, par_NS, score_NS, position, resTable):

	if position % 2 == 1:
		par = -par_NS
		score = -score_NS
		posFactor = -1
	else:
		par = par_NS
		score = score_NS
		posFactor = 1

	utility = score - par

	if utility == 0:
		return outputHistory

	target = []
	display = []
	prevFeas = True
	for i in range (len (outputHistory)):
		output = outputHistory [i]
		# for j in range (len (output)):
		# 	output [j] = 0.
		# target.append (output)
		# continue
		(prev_bid, choice, legalBids) = moveHistory [i]
		
		# penalty = 1 * reward / len (legalBids)
		temp = []
		if utility < 0:
			if i + 1 < len (outputHistory):
				(if_bid, _, nextLegalBids) = moveHistory [i + 1]
				feasible = False
				for j in nextLegalBids:
					if_bid_copy = if_bid.copy ()
					if_bid_copy.append (possible_bids [j])
					if getScore (if_bid_copy + ["P", "P", "P"], resTable) * posFactor >= par:
						feasible = True
						break
			else:
				feasible = True	

			if _DEBUG > 2:
				print ("Prev_bid, feasible:", prev_bid, feasible)
			if not feasible and prevFeas:
				for j in legalBids:
					if j == choice:
						output [j] = 0
					else:
						output [j] = output [j]
					temp.append (str (output [j])[:4])
			else:
				for j in legalBids:
					temp.append (str (output [j])[:4])
			prevFeas = feasible
		if utility > 0:
			for j in legalBids:
				if j == choice:
					output [j] = 1
				else:
					output [j] = output [j]
				temp.append (str (output [j])[:4])
			# output [j] = output [j] * np.exp (penalty)
		
		target.append (output)
		display.append (temp)
	if _DEBUG > 2:
		print ("Target\n", display)
	return target

def getScore (bids, resTable):

	if bids == ['P','P','P','P']:
		return 0

	double = 0
	level = 0
	suit = -1
	player = -1
	side = -1
	suit_conv = {'S': 0, "H": 1, "D": 2, "C": 3, "N": 4}
	first_NS = [-1,-1,-1,-1,-1]
	first_EW = [-1,-1,-1,-1,-1]

	for bid in bids:
		player += 1
		if player == 4:
			player = 0
		# print ("player, bid", player, bid)
		if bid == "P":
			continue
		if bid == "X":
			double = 1
			continue
		if bid == "XX":
			double = 2 
			continue
		double = 0
		try:
			level = int (bid [0])
			suit = suit_conv [bid [1]]
		except:
			print (bids)
			print ("Bid Error -- getScore, Game.py, 129")
		if player % 2 == 0:
			if first_NS [suit] == -1:
				first_NS [suit] = player
			side = 0
		else:
			if first_EW [suit] == -1:
				first_EW [suit] = player
			side = 1

	if side == 0:
		decl = first_NS [suit]
	else:
		decl = first_EW [suit]

	result = resTable [suit * 4 + decl]
	# print ("side, level, suit, decl", side, level, suit, decl)
	score = calcScore (level, suit, double, result)
	if side != 0:
		score *= -1
	return score

def learn (network, results, par, score, resTable):
	# results = [(position, agent_feedback) NESW]
	# agent_feedback = ([inputHistory],[outputHistory],[moveHistory])
	# par = NS perspective

	Y_true = [] #target
	X = []
	inputHis = [[],[]]
	outputHis = [[],[]]
	moveHis = [[],[]]

	max_counter = -1
	for result in results:
		(pos, feedback) = result
		(inputHistory, outputHistory, moveHistory) = feedback
		if len (inputHistory) > max_counter:
			max_counter = len (inputHistory)

	movecounter = 0
	while movecounter < max_counter:
		res_counter = 0
		while res_counter < len (results):
			(pos, feedback) = results [res_counter]
			(inputHistory, outputHistory, moveHistory) = feedback
			if movecounter < len (inputHistory):
				inputHis [pos % 2].append (inputHistory [movecounter])
				outputHis [pos % 2].append (outputHistory [movecounter])
				moveHis [pos % 2].append (moveHistory [movecounter])
			res_counter += 1
		movecounter += 1


	# print (inputHis)
	# print (outputHis)
	# print (moveHis)

	for i in range (2):
		inputHistory = inputHis [i]
		outputHistory = outputHis [i]
		moveHistory = moveHis [i]
		X = X + inputHistory
		target = setTarget (outputHistory, moveHistory, par, score, i, resTable)
		Y_true = Y_true + target

	if K.backend () == "tensorflow":
		x = np.asarray (X)
		y = np.asarray (Y_true)


	# print ("X_SHAPE", x.shape)
	# print ("Y_SHAPE", y.shape)
	# session = tf.Session()
	# print (session.run (custom_loss(network.predict (x), y)))
	# print (network.predict (x))
	# print ("------")

	network.fit (x, y, epochs = 1, verbose = 1)

	# print (session.run (custom_loss(network.predict (x), y)))
	# print (network.predict (x))
	return

def main ():

	NETWORK_1 = "../data/Networks/RL/Gen_1/network2.h5"
	NETWORK_2 = "../data/Networks/RL/Gen_1/network2.h5"
	NETWORK_3 = ""
	NETWORK_4 = ""

	BIDDING_1 = "../data/Networks/RL/Gen_1/bidding2"
	BIDDING_2 = "../data/Networks/RL/Gen_1/bidding2"
	BIDDING_3 = ""
	BIDDING_4 = ""

	# network_1 = loadNetwork (NETWORK_1)
	# biddingBase_1 = loadBiddingBase (BIDDING_1)
	network_1 = loadNetwork ("")
	biddingBase_1 = loadBiddingBase ("")



	agent_1 = Agent (network_1, biddingBase_1)
	# agent_2 = Agent (network_1, biddingBase_1)
	agent_3 = Agent (network_1, biddingBase_1)
	# agent_4 = Agent (network_1, biddingBase_1)
	agent_2 = Dummy ()
	agent_4 = Dummy ()

	agents = [agent_1, agent_2, agent_3, agent_4]
	for agent in agents:
		agent.setCoefficient (BIDDING_ALPHA, EXPLORE_COEFFICIENT)

	episodes = 10000
	# deal = gd.genDeal ()
	# gd.printHand (deal)
	# (par, resTable) = gd.getPar (deal)
	# print (resTable)

	# deal = gd.genDeal ()
	# deal = gd.getDealFromPreset (0)
	for i in range (episodes):
		deal = gd.genDeal ()
		giveHands (agents, gd.getHand(deal))
		bids = play (agents)
		results = []
		counter = -1
		for agent in agents:
			counter += 1
			if counter % 2 != 0:
				continue
			results.append ((counter, agent.feedback ()))

		(par, resTable) = gd.getPar (deal)
		score = getScore (bids, resTable)
		learn (network_1, results, par, score, resTable)
		writeBiddingBase (biddingBase_1, BIDDING_1)
		print (bids)
		print (par, score)
		print ("----")
		saveNetwork (network_1, NETWORK_1)

main ()
K.clear_session ()
