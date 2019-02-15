#!usr/bin/python
# -*- coding: utf-8 -*-

import logging

import networkx as nx
import random
import numpy as np
import time

from TriangulationAlgorithms import TriangulationAlgorithm as ta
from TriangulationAlgorithms import CMT

def triangulate_EG(G, randomized=False, repetitions=1, reduce_graph=True, timeout=-1):
	algo = Algorithm_EliminationGame(G, reduce_graph, timeout)
	if not randomized:
		algo.run()
		return {
			"H" : algo.get_triangulated(),
			"size" : len(algo.get_triangulation_edges()),
			"mean" : len(algo.get_triangulation_edges()),
			"variance" : 0,
			"repetitions" : 1
			}
	else:
		H_opt = None
		size_opt = None
		all_sizes = []
		for i in range(repetitions):
			algo.run_randomized()
			all_sizes.append(len(algo.get_triangulation_edges()))
			if H_opt == None or len(algo.get_triangulation_edges()) < size_opt:
				H_opt = algo.get_triangulated()
				size_opt = len(algo.get_triangulation_edges())
		return {
			"H" : H_opt,
			"size" : size_opt,
			"mean" : np.mean(all_sizes),
			"variance" : np.var(all_sizes),
			"repetitions" : repetitions
			}
	
def triangulate_EGPLUS(G, randomized=False, repetitions=1, reduce_graph=True, timeout=-1):
	'''
	run Elimination Game, but minimize the result using CMT
	'''
	algo = Algorithm_EliminationGame(G, reduce_graph, timeout)
	minimizer = CMT.Algorithm_CMT(G)
	if not randomized:
		algo.run()
		F = minimizer.minimize_triangulation(G, algo.get_triangulation_edges(), False)
		H = G.copy()
		H.add_edges_from(F)

		return {
			"H" : H,
			"size" : len(F),
			"mean" : len(F),
			"variance" : 0,
			"repetitions" : 1
			}
	else:
		H_opt = None
		size_opt = None
		all_sizes = []
		for i in range(repetitions):
			algo.run_randomized()
			for j in range(repetitions):
				F = minimizer.minimize_triangulation(G, algo.get_triangulation_edges(), True)
				H = G.copy()
				H.add_edges_from(F)
				
				all_sizes.append(len(F))
				if H_opt == None or len(F) < size_opt:
					H_opt = H
					size_opt = len(F)
		return {
			"H" : H_opt,
			"size" : size_opt,
			"mean" : np.mean(all_sizes),
			"variance" : np.var(all_sizes),
			"repetitions" : repetitions*repetitions
			}
	
class Algorithm_EliminationGame(ta.TriangulationAlgorithm):
	def __init__(self, G, reduce_graph=True, timeout=-1):
		logging.info("=== EG.Algorithm_EliminationGame.init ===")
		super().__init__(G, reduce_graph, timeout)
	
	def triangulate(self, G, randomized=False, alpha=None):
		'''
		The elimination game algorithm for computing a triangulation algorithm
		
		Args:
			G : the input graph in networkx format
			alpha : an ordering of the nodes that defines the order in which the nodes are processed, as a dict {node: position}
			randomized : if no ordering alpha is specified and randomized is set to True, the order of the nodes is shuffled
	
		Returns:
			F : a set of edges such that G + F is a minimum triangulation of G
		'''
		logging.info("=== elimination_game_triangulation ===")
		logging.debug("Alpha: "+str(alpha))
		
		if alpha == None:
			all_nodes = [n for n in G]
			if randomized:
				random.shuffle(all_nodes)
			self.alpha = {}
			i = 0
			for n in all_nodes:
				self.alpha[n] = i
				i += 1
		else:
			all_nodes = sorted([n for n in alpha.keys()], key=lambda x: alpha[x])
			self.alpha = alpha
		G_temp = G.copy()
		F = []
		for node in all_nodes:
			# check timeout:
			if self.timeout > 0 and time.time() > self.timeout:
				raise ta.TimeLimitExceededException("Time Limit Exceeded!")

			all_neighbors = [n for n in G_temp.neighbors(node)]
			for i in range(0, len(all_neighbors)):
				for j in range(i+1, len(all_neighbors)):
					edge_between_neighbors = (all_neighbors[i], all_neighbors[j])
					if edge_between_neighbors not in G_temp.edges():
						G_temp.add_edges_from([edge_between_neighbors])
						F.append(edge_between_neighbors)
						logging.debug("Added edge: "+str(edge_between_neighbors))
			G_temp.remove_node(node)
			logging.debug("removed node: "+str(node))
			
		return F