#!usr/bin/python
# -*- coding: utf-8 -*-

import logging

import networkx as nx

import graph_meta as gm
import TriangulationAlgorithm as ta

def find_minimum_triangulation(G, n=None):
	mt = Algorithm_MinimumTriangulation(G)
	mt.run()
	return mt.get_triangulated()

def get_minimum_triangulation_size(G, n=None):
	mt = Algorithm_MinimumTriangulation(G)
	mt.run()
	return len(mt.edges_of_minimum_triangulation)

class MT_TooLargeCycleError(Exception):
	'''
	Custom error type that gets thrown when the input graph contains a cycle that is too large.
	This is intended to prevent running out of memory (and out of time),
	since memory requirement of this algorithm is in O(2^k), where k < |E(G)| is the length of the largest basic cycle in G.
	Time complexity is in O(2^n), with n = |G|.
	'''
	
class MT_Chordedge:
	'''
	Datastructure to represent a possible chord-edge of one (or more) cycles of the graph
	Stores all cycles for which this edge is a chord
	
	Args:
		node_v , node_u : two graph nodes in networkx-format that define the edge
		
	Attributes:
		node_v, node_u : the nodes that define the edge
		is_in_graph : a bool that describes whether this edge is currently contained in the triangulation or not
		cycle_indices : a list of ints that contains all indices of cycles (type MT_Cycle) for which this edge is a chord-edge
		induced_cycles : a list of integers that contains all indices of cycles that are not in the base graph but can appear once this edge is in the graph.
	'''
	def __init__(self, node_v, node_u):
		logging.info("=== MT_Chordedge.init ===")
		self.node_v = node_v
		self.node_u = node_u
		self.is_in_graph = False
		self.cycle_indices = []
		self.induced_cycles = []

	def add_cycle(self, cycle_id):
		self.cycle_indices.append(cycle_id)

	def get_edge(self):
		return (self.node_v, self.node_u)

	def __getitem__(self, key):
		if key == 0:
			return self.node_v
		elif key == 1:
			return self.node_u
		else:
			return None
	
	def __str__(self):
		return "("+str(self.node_v)+","+str(self.node_u)+")"

class MT_Cycle(gm.Cycle):
	'''
	Datastructure to represent a cycle of the graph
	Stores all possible chord-edges and the resulting subcycles once they have been computed
	
	Is hashable.
	
	Args:
		cyclenodes : a list of nodes in networkx-format that form a cycle in the original graph.
		
	Attributes:
		cyclenodes : the list of nodes that define this cycle
		chordedge_ids : a list of ints that contains all indices of chord-edges (type MT_Chordedge) that are chords for this cycle
		is_in_graph : a bool that describes whether this cycle is currently contained unsplit in the triangulation or not
		subcycles : a dict {chord_edge_id (int) : subcycle_ids(list(int))} that maps chordedge-indices to lists subcycle-indices, where each subcycle-indexdescribes a cycle that is created when this cycle is split by the chordedge defined by chord_edge_id
		required_chordedges : a list of ints that contain all indices of chordedges that have to be in the graph for this cycle to appear.
	'''
	def __init__(self, cyclenodes):
		logging.info("=== MT_Cycle.init ===")
		gm.Cycle.__init__(self,cyclenodes)
		#self.cyclenodes = cyclenodes
		self.chordedge_ids = []
		self.is_in_graph = True
		self.subcycles = {}
		self.required_chordedges = []

	def add_chord(self, chord_id):
		self.chordedge_ids.append(chord_id)

	#def set_as_split(self, chord_id, list_of_subcycle_ids):
	#	self.subcycles[chord_id] = list_of_subcycle_ids

class Algorithm_MinimumTriangulation(ta.TriangulationAlgorithm):
	'''
	This class contains the methods to compute a minimum triangulation and handles all the neccessary datastructures.
	Note that the current working graph is not explicitly stored, as it follows from G and the subset of chordedges of F that are flagged with is_in_graph = True.
	
	Args:
		G : a graph in networkx-format for which a minimum triangulation should be computed
		
	Attributes:
		G : the graph
		F : a list of edges in networkx-format. This list contains all the possible chord-edges (type MT_Chordedge) that can be added to G
		cycles : a list of cycles (type MT_Cycle) that are contained in G or in any graph constructed from G by inserting chordedges
		cycle_ids : a dict {cycle (MT_Cycle) : cycle_id(int)} that maps each cycle to its id in the list of cycles.
		number_of_nonchordal_cycles : an int describing the number of cycles of length > 3 that are contained in the current working graph.
		chord_adjacencies : a dict {node, node : chord_id} that maps tuples of nodes to indices of chords, if the two nodes are connected by a possible chord-edge from the set F.
	'''
	def __init__(self, G):
		logging.info("=== MT_MinimumTriangulation.init ===")
		self.G = G

		self.F = []
		self.cycles = []
		self.cycle_ids = {}
		self.number_of_nonchordal_cycles = 0
		self.chord_adjacencies = {}

		self.edges_of_triangulation = []
		
	def get_triangulated(self):
		H = self.G.copy()
		H.add_edges_from(self.edges_of_triangulation)
		return H

	def run(self):
		'''
		Finds a minimum triangulation of G, by checking each possible order of inserting chord-edges into the graph G until G is chordal.
	
		Running time in O(poly(n) * 2^n), where n = |G|.
		'''
		logging.info("=== MT_MinimumTriangulation.run ===")
		
		# initialize a database
		self.init_cycle_chord_database()
		
		# initialize stack of currently considered edges:
		current_edge_stack = []
		# initialize map of edgesets:
		chordality_check = {}
        
		# initialize stack of added chord-edges
		chord_stack = []
		
		# initialize minimum triangulation chordset:
		minimum_triangulation_size = -1
		minimum_triangulation_chordset = []
        
		#current_cycle_id = 0
		#current_chord_in_cycle_id = 0
		current_chord_id = 0
		terminated = nx.is_chordal(self.G) or len(self.cycles) == 0
		while not terminated:
			logging.debug("=*= NEXT ITERATION =*=")
			logging.debug("Current cycles in the graph:")
			for cycle_id in range(len(self.cycles)):
				logging.debug(" "+str(cycle_id)+" : "+str(self.cycles[cycle_id])+" ["+str(self.cycles[cycle_id].is_in_graph)+"]")
			logging.debug("Current number of nonchordal cycles: "+str(self.number_of_nonchordal_cycles))
			
			logging.debug("Current chords in the graph:")
			for chord in [e for e in self.F if e.is_in_graph]:
				logging.debug(chord)
				
			# get next chord that is
			# a) not in graph and
			# b) would split a cycle
			current_chord_id = self.get_next_chord(current_chord_id)
			logging.debug("Current chord: "+str(current_chord_id)+": "+str(self.F[current_chord_id]))
        
			# if such a chord exist, set the current_chord_id to this chord
			#	split all cycles that contain this chord
			#	check if graph is chordal.
			#		if chordal, check if current edge set is minimum
			# 		else add current_chord_id and a list of all split cycles to chord_stack
			# otherwise
			#	pop the next tuple from the stack
			#	merge all cylces that were split by that last operation from the stack
			
			if current_chord_id >= len(self.F):
				terminated = True
				logging.debug("Current id larger than total number of chords. Terminate.")
				break
				
			elif current_chord_id >= 0:
				logging.debug("Add this chord to graph.")
				cycles_to_split = [cycle_id for cycle_id in self.F[current_chord_id].cycle_indices if self.cycles[cycle_id].is_in_graph]
				chord_stack.append((current_chord_id, cycles_to_split))
				for cycle_id in cycles_to_split:
					self.split_cycle(cycle_id, current_chord_id)
					# set chord as added:
					self.F[current_chord_id].is_in_graph = True
					# compute current set of cycles:
					G_temp = self.G.copy()
					G_temp.add_edges_from([e.get_edge() for e in self.F if e.is_in_graph])
					all_cycles = gm.get_all_cycle_from_cycle_basis(G_temp)
					for cycle in all_cycles:
						cycle_c = MT_Cycle(cycle)
						if cycle_c not in self.cycles:
							next_cycle_id = len(self.cycles)
							self.cycles.append(cycle_c)
							self.F[current_chord_id].induced_cycles.append(next_cycle_id)
							self.init_cycle_chord_database_for_cycle(next_cycle_id)

					# check if graph is chordal:
					if self.number_of_nonchordal_cycles == 0:
						# check if current edge set has minimum size so far:
						currently_included_chordedges = [e for e in self.F if e.is_in_graph]
						if minimum_triangulation_size < 0 or minimum_triangulation_size > len(currently_included_chordedges):
							minimum_triangulation_size = len(currently_included_chordedges)
							minimum_triangulation_chordset = currently_included_chordedges
						
			elif len(chord_stack) > 0:
				logging.debug("Remove last chord from graph.")
				(current_chord_id, last_split_cycles) = chord_stack.pop()
				logging.debug("Last added chord: "+str(current_chord_id)+": "+str(self.F[current_chord_id]))

				# merge previously split cycles:
				for cycle_id in last_split_cycles:
					self.merge_cycle(current_chord_id, cycle_id)
				# remove induced cycles:
				for cycle_id in self.F[current_chord_id].induced_cycles:
					self.cycles[cycle_id].is_in_cycle = False
					for chord_id in self.cycles[cycle_id].chordedge_ids:
						self.F[chord_id].cycle_indices.remove(cycle_id)
				self.F[current_chord_id].induced_cycles = []
				
				self.F[current_chord_id].is_in_graph = False
				current_chord_id += 1
				
			else:
				logging.debug("All possibilities are evaluated. Terminate.")
				terminated = True
		
		self.edges_of_triangulation = [e.get_edge() for e in minimum_triangulation_chordset]

	def init_cycle_chord_database(self):
		'''
		Initialized the database containing all cycles and possible chord-edges
		as well as the information which chord is contained in which cycles.
		'''
		logging.info("=== MT_MinimumTriangulation.init_cycle_chord_database ===")
		
		# Get all chordless cycles of G:
		self.cycles = [MT_Cycle(c) for c in gm.get_all_cycle_from_cycle_basis(self.G)]#get_all_cycles()
		logging.debug("All cycles of G:")
		for c in self.cycles:
			logging.debug(c)
		
		self.cycle_ids = {self.cycles[i] : i for i in range(len(self.cycles))}
		
		# Check the maximum cycle length. If the largest cycle contains more than 16 nodes, abort.
		if len(self.cycles) > 0:
			maximum_cycle_length = max([len(c) for c in self.cycles])
			if maximum_cycle_length > 16:
				raise MT_TooLargeCycleError("Maximum cycle length too large")
		
		self.number_of_nonchordal_cycles = len(self.cycles)
		# Construct set of all possible chord edges for G:
		# and the database describing chord-cycle-relationships
		for cycle_id in range(len(self.cycles)):
			logging.debug("Current chord_id data:")
			for key in self.chord_adjacencies:
				logging.debug(str(key)+ " : " +str(self.chord_adjacencies[key]))
			self.init_cycle_chord_database_for_cycle(cycle_id)
	
	def init_cycle_chord_database_for_cycle(self, cycle_id):
		'''
		Initialize the database for a single cycle.
		
		Args:
			cycle_id : The id of the cycle for which the database is initialized.
		'''
		logging.info("=== MT_MinimumTriangulation.init_cycle_chord_database_for_cycle ===")
		logging.info("Init cycle chord database for cycle "+str(cycle_id)+": "+str(self.cycles[cycle_id]))
		
		#logging.debug("Current chord_id data:")
		#for key in self.chord_adjacencies:
		#	logging.debug(str(key)+ " : " +str(self.chord_adjacencies[key]))
		
		cycle = self.cycles[cycle_id]
		for i in range(len(cycle)):
			if cycle[i] not in self.chord_adjacencies:
				self.chord_adjacencies[cycle[i]] = {}
			for j in range(i+2, len(cycle)):
				if i == 0 and j == len(cycle)-1:
					break
				if cycle[j] not in self.chord_adjacencies[cycle[i]]:
					if cycle[j] not in self.chord_adjacencies:
						self.chord_adjacencies[cycle[j]] = {}
					current_chord_id = len(self.F)
					self.chord_adjacencies[cycle[i]][cycle[j]] = current_chord_id
					self.chord_adjacencies[cycle[j]][cycle[i]] = current_chord_id
					self.F.append(MT_Chordedge(cycle[i],cycle[j]))
				else:
					current_chord_id = self.chord_adjacencies[cycle[i]][cycle[j]]
				logging.debug("Add chord "+str(current_chord_id)+" ("+str(cycle[i])+","+str(cycle[j])+") to this cycle.")
				self.F[current_chord_id].add_cycle(cycle_id)
				self.cycles[cycle_id].add_chord(current_chord_id)

	def split_cycle(self, cycle_id, chord_id):
		'''
		Splits a cycle into two subcycles by a given edge.
		
		Args:
			cycle_id : the cycle to split
			chord_id : the chord that splits the cycle
		'''
		logging.info("=== MT_MinimumTriangulation.split_cycle ===")
		logging.info("split cycle "+str(cycle_id)+": "+str(self.cycles[cycle_id])+" at chord "+str(chord_id)+": "+str(self.F[chord_id]))

		if chord_id in self.cycles[cycle_id].subcycles:
			# get ids of subcycles
			for subcycle_id in self.cycles[cycle_id].subcycles[chord_id]:
				self.cycles[subcycle_id].is_in_graph = True
				self.number_of_nonchordal_cycles += 1
		else:
			# compute new subcycles:
			nodes_new_cycles = self.get_subcycles(cycle_id, chord_id)
			
			if chord_id not in self.cycles[cycle_id].subcycles:
				self.cycles[cycle_id].subcycles[chord_id] = []
			
			for i in range(2):
				if len(nodes_new_cycles[i]) > 3:
					subcycle = MT_Cycle(nodes_new_cycles[i])
					if subcycle not in self.cycle_ids:
						logging.debug("create new cycle for subsycle "+str(i+1)+": "+str(subcycle))
						subcycle_id = len(self.cycles)
						self.cycles.append(subcycle)
						self.cycle_ids[subcycle] = subcycle_id
						self.init_cycle_chord_database_for_cycle(subcycle_id)
						self.number_of_nonchordal_cycles += 1
					else:
						subcycle_id = self.cycle_ids[subcycle]
						if not self.cycles[subcycle_id].is_in_graph:
							self.cycles[subcycle_id].is_in_graph = True
							self.number_of_nonchordal_cycles += 1
					logging.debug("Add subcycle "+str(subcycle_id)+" to chord "+str(chord_id)+" of cycle "+str(cycle_id))
					self.cycles[cycle_id].subcycles[chord_id].append(subcycle_id)

		# set cycle as removed:
		self.cycles[cycle_id].is_in_graph = False
		self.number_of_nonchordal_cycles -= 1
			
	def merge_cycle(self, chord_id, cycle_id):
		'''
		Merges two cycle along a chord, removes the chord from the graph
		
		Args:
			chord_id : the chord that is removed from the graph
			cycle_id : the cycle that is recreated by merging its subcycles
		'''
		logging.info("=== MT_MinimumTriangulation.merge_cycle ===")
		logging.info("Merge cycles into cycle "+str(cycle_id)+" at chord "+str(chord_id))
		
		self.cycles[cycle_id].is_in_graph = True
		self.number_of_nonchordal_cycles += 1
		for subcycle_id in self.cycles[cycle_id].subcycles[chord_id]:
			self.cycles[subcycle_id].is_in_graph = False
			self.number_of_nonchordal_cycles -= 1
			
	def get_subcycles(self, cycle_id, chord_id):
		'''
		Constructs the lists of nodes that define the subcycles of a cycle
		
		Args:
			cycle_id : the index of the parent cycle
			chord_id : the index of the chord that splits the cycle
			
		Return:
			A list of lists of integer, each containing the nodes of a subcycle
		'''
		logging.info("=== MT_MinimumTriangulation.get_subcycles ===")
		
		nodes_new_cycles = [[],[]]
		id_v = -1
		id_u = -1
		i = -1
		cycle = self.cycles[cycle_id]
		for node in cycle:
			i += 1
			if node == self.F[chord_id][0]:
				id_v = i
			if node == self.F[chord_id][1]:
				id_u = i
		nodes_new_cycles[0] = cycle[:min(id_v,id_u)+1]+cycle[max(id_v,id_u):]
		nodes_new_cycles[1] = cycle[min(id_v,id_u):max(id_v,id_u)+1]
		logging.debug("nodes first subcycle: "+str(nodes_new_cycles[0]))
		logging.debug("nodes second subcycle: "+str(nodes_new_cycles[1]))
			
		return nodes_new_cycles
		
	def get_next_chord(self, current_chord_id):
		'''
		Get the id of the next chord that is not in the graph and would still split a cycle
		
		Args:
			current_chord_id : the current chord id, from which the search starts
			
		Return:
			A valid chord index conform to the specification above, if it exists. -1 otherwise.
		'''
		logging.info("=== MT_MinimumTriangulation.get_next_chord ===")
		found_next_chord = False
		while current_chord_id < len(self.F):
			if not self.F[current_chord_id].is_in_graph:
				for cycle_id in self.F[current_chord_id].cycle_indices:
					if self.cycles[cycle_id].is_in_graph:
						return current_chord_id
			current_chord_id += 1
		return -1
