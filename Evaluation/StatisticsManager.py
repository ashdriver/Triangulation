#!usr/bin/python
# -*- coding: utf-8 -*-

import numpy as np
import json
import csv
import re
import os

try:
	import tkinter
except ImportError:
	import matplotlib
	matplotlib.use('agg')
	import matplotlib.pyplot as plt
else:
	import matplotlib.pyplot as plt
	import matplotlib.lines as mlines

from Evaluation import GraphDataOrganizer as gdo
from Evaluation import ExperimentManager as em
from MetaScripts import meta
from MetaScripts import global_settings as gs

def load_axis_data_from_file(filename, axis, keep_nulls=False, cutoff_at_timelimit=False):
	'''
	loads evaluation data from a file

	args:
		filename: the filename
		axis: "OUTPUT" or "TIME", defines which data to load
		keep_nulls: if False, null-entries are removed from the data before returning
		cutoff_at_timelimit : if True, evaldata that terminated with exceeded timelimit is considered as not terminated

	return:
		a list of numbers
	'''
	with open(filename) as jsonfile:
		this_file_data = json.load(jsonfile)
	
	if not cutoff_at_timelimit:
		if axis=="OUTPUT":
			data = [d["output"] for d in this_file_data]
		elif axis=="TIME":
			data = [d["running_time"] for d in this_file_data if d["running_time"]>0]
	else:
		if axis=="OUTPUT":
			data = [d["output"] if d["running_time"] < d["timelimit"] else -1 for d in this_file_data]
		elif axis=="TIME":
			data = [d["running_time"] if d["running_time"] > 0 and d["running_time"] < d["timelimit"] else d["timelimit"] for d in this_file_data]

	if not keep_nulls:
		return [d for d in data if d>0]
	else:
		return data

def get_algo_name_from_filename(filename):
	'''
	parses a filename of a EvalData file to get the name of the algorithm
	'''
	algo_parts = re.split('_',filename)
	algo_name = algo_parts[2]
	b_id = 3
	if algo_parts[3][0] == "R":
		algo_name += "_"+algo_parts[3]
		b_id += 1
	if algo_parts[b_id] == "B":
		algo_name += "_B"
	return algo_name

def load_evaldata_from_json(basedir, filename):
	'''
	Loads the Evaldata from a specific file
	'''
	graphdataset = []
	evaldataset = []
	filepath = basedir+"/results/"+filename
	if not "json" in filepath:
		filepath+=".json"
	with open(filepath,"r") as jsonfile:
		dataset = json.load(jsonfile)
		for data in dataset:
			graph_id = re.split(r'\.',data["input_id"])[0]
			if graphdataset == []:
				graphdatafile = "_".join(re.split(r'_',data["input_id"])[:-1])+".json"
				graphdataset = gdo.load_graphs_from_json(basedir+"/input/"+graphdatafile)
			graphdata = None
			for gd in graphdataset:
				gd.id = re.split(r'\.', gd.id)[0]
				if gd.id == graph_id:
					graphdata = gd
					break
			if "reduce_graph" not in data:
				data["reduce_graph"] = True
			if "timelimit" not in data:
				data["timelimit"] = -1
			if "randomized" not in data:
				data["randomized"] = False
			if "repetitions" not in data:
				data["repetitions"] = 1
			if "algo" in data:
				evaldata = em.EvalData(data["algo"], graphdata, data["randomized"], data["repetitions"], data["reduce_graph"], data["timelimit"])
			else:
				evaldata = em.EvalData("generic", graphdata)
			evaldata.set_results(data["output"], data["running_time"])
			if "output mean" in data:
				evaldata.out_mean = data["output mean"]
			if "output variance" in data:
				evaldata.out_var = data["output variance"]
			evaldataset.append(evaldata)
	return evaldataset
	
def load_data(graphclass="general", density_class="dense", n=None, p=None, rel_m=None, d=None, c=None, algocode=None, randomized=False, rand_reptetions=None, reduced=False, axis="OUTPUT", keep_nulls=False, cutoff_at_timelimit=False):
	'''
	loads all data from the evaldata-database that is conform to the specified parameters.
	
	args:
		n, p, rel_m, d, c: restrictions on the subclass of graphs.
			Only restrictions that are not "None" are considered.
		axis: "OUTPUT" or "TIME", defines which data to load
		keep_nulls: if False, null-entries are removed from the data before returning
		cutoff_at_timelimit : if True, evaldata that terminated with exceeded timelimit is considered as not terminated		
	'''
	logging.debug("sm.load_data")
	
	if not graphclass in gs.GRAPH_CLASSES:
		raise gdo.ParameterMissingException("Wrong parameter: graphclass: "+graphclass)
		
	if not density_class in ["dense", "sparse"]:
		raise gdo.ParameterMissingException("Wrong parameter: density_class: "+density_class)
	
	if p == None and rel_m == None:
		raise ParameterMissingException("Missing parameters in initialization: p or rel_m")
		
	if graphclass == "planar" and density_class == "dense":
		raise gdo.ParameterMissingException("Incompatible parameters: graphclass: planar and density_class: dense")
		
	if graphclass == "maxdeg" and d == None:
		raise ParameterMissingException("Missing parameters in initialization: d")
		
	if graphclass == "maxclique" and c == None:
		raise ParameterMissingException("Missing parameters in initialization: c")
		
	if algocode not in gs.BASE_ALGO_CODES:
		raise ParameterMissingException("Wrong parameter: algocode: "+algocode)
	
	if randomized and rand_repetions == None:
		raise ParameterMissingException("Missing parameters in initialization: rand_reptetions")
		
	base_dir = "data/eval/results/result_"+graphclass
		
	if n == None:
		options_for_n = gs.GRAPH_SIZES
	else:
		options_for_n = [n]
	
	if density_class == "dense":
		if p == None:
			if graphclass == "general":
				options_for_p = gs.GRAPH_DENSITIY_P
			elif graphclass == "maxdeg" or graphclass == "maxclique":
				options_for_p = gs.BOUNDEDGRAPHS_DENSITY_P
		else:
			options_for_p = [p]
	else:
		options_for_p = [-1]
		
	if density_class == "sparse":
		if rel_m == None:
			options_for_relm = gs.SPARSE_DENSITY_RELM
		else:
			options_for_relm = [rel_m]
	else:
		options_for_relm = [-1]
			
	if graphclass == "maxdeg":
		if d == None:
			options_for_d = gs.MAXDEGREE_SETTINGS
		else:
			options_for_d = [d]
	else:
		options_for_d = [-1]
			
	if graphclass == "maxclique":
		if c == None:
			options_for_c = gs.MAXCLIQUE_SETTINGS
		else:
			options_for_c = [c]
	else:
		options_for_c = [-1]
			
	data = {}
	for n in options_for_n:
		for p in options_for_p:
			for rel_m in options_for_relm:
				for d in options_for_d:
					for c in options_for_c:
						if density_class == "dense":
							p_as_string = p_as_string = "{0:.2f}".format(p)
							graph_base_filename = "dense_n"+str(n)+"_p"+p_as_string
						elif density_class == "sparse":
							graph_base_filename = "sparse_n"+str(n)+"_relm"+str(parameters["rel_m"])
							if graphclass == "maxdeg":
								graph_base_filename += "_d"+str(d)
							if graphclass == "maxclique":
								graph_base_filename += "_c"+str(c)
						graph_filename = re.sub('\.','', graph_base_filename)
						extended_algo_code = algocode
						if randomized:
							extended_algo_code += "_R"+str(rand_reptetions)
						if not reduced:
							extended_algo_code += "_B"
							
						evaldata_filename = "results_"+extended_algo_code
						filepath = base_dir+"/"+evaldata_filename+".json"
						data[n][p][rel_m][d][c][density_class] = extended_algo_code(filepath, axis, keep_nulls, cutoff_at_timelimit)
	return data								
				
def compute_statistics(datadir):
	'''
	Computes relevant statistic from all EvalData files in a specific directory.
	Constructs a list of dicts that contains a dictionary for each file in the directory.
	Each dictionary contains data of the based experiment (graph data, algorithm data)
	as well as some computed statistics like mean and variance of fill-in size and runtime.
	Also writes these statistics to a file

	return:
		columns : contains the keys of the constructed dictionaries
		stats : contains the data
	'''
	logging.debug("Compute statistics for results in "+datadir)

	stats = []
	columns = ["graph id", "avg n", "avg m", "algorithm", "reduced", "repeats", "time limit", "mean time", "var time", "moo", "voo", "mmo", "mvo", "success (\%)"]
	progress = 0
	allfiles = [file for file in os.listdir(datadir+"/results") if ".json" in file]
	for file in allfiles:
		meta.print_progress(progress, len(allfiles))
		progress += 1

		filename = re.split(r'\.', file)[0]
		evaldata = load_evaldata_from_json(datadir, filename)
		graph_id = "_".join(re.split(r'_',evaldata[0].id)[:-1])
		avg_n = np.mean([data.n for data in evaldata])# if data.output >= 0])
		avg_m = np.mean([data.m for data in evaldata])# if data.output >= 0])
		timelimit = evaldata[0].timelimit
		mean_time = np.mean([data.running_time for data in evaldata if data.output >= 0])
		var_time = np.var([data.running_time for data in evaldata if data.output >= 0])
		mean_output = np.mean([data.output for data in evaldata if data.output >= 0])
		var_output = np.var([data.output for data in evaldata if data.output >= 0])
		repeats = evaldata[0].repetitions
		mmo = np.mean([data.out_mean for data in evaldata if data.out_mean >= 0])
		mvo = np.mean([data.out_var for data in evaldata if data.out_var >= 0])
		algo_name = evaldata[0].algo
		if evaldata[0].is_randomized:
			algo_name += " (R)"

		if mmo == mean_output:
			mmo = "N/A"
			mvo = "N/A"

		success = 100*float(len([data.output for data in evaldata if data.output >= 0]))/float(len([data.output for data in evaldata]))

		newstats = {
			"algorithm" : algo_name,
			"reduced" : str(evaldata[0].reduce_graph),
			"graph id" : graph_id,
			"avg n" : avg_n,
			"avg m" : avg_m, 
			"mean time" : mean_time,
			"var time" : var_time,
			"moo" : mean_output,
			"voo" : var_output,
			"repeats" : repeats,
			"mmo" : mmo,
			"mvo" : mvo,
			"time limit" : timelimit,
			"success (\%)": success
		}
		for key in newstats:
			if not isinstance(newstats[key], str) and np.isnan(newstats[key]):
				newstats[key] = "N/A"

		stats.append(newstats)
	write_stats_to_file(datadir, stats)

	return (columns, stats)
			
def construct_output_table(columns, dataset, outputfilename="out.tex"):
	'''
	Constructs a tex-file containing a table that contains the statistics
	computed by the method "compute_statistics" above
	'''
	# sort dataset:
	sorteddataset = sorted(dataset, key=lambda data: (data["avg n"], data["graph id"], data["algorithm"], data["repeats"], data["reduced"]))

	texoutputstring = ""
	with open("tex_template.txt", "r") as tex_template:
		for line in tex_template:
			texoutputstring += line

	tabulardefline = "\\begin{longtable}{"
	for c in columns:
		tabulardefline += "c"
	tabulardefline += "}"
	texoutputstring += tabulardefline+"\n"

	tabheadline = columns[0]
	for i in range(1,len(columns)):
		tabheadline += " & "+columns[i]
	tabheadline += " \\\\ \\hline \n"
	texoutputstring += tabheadline
	#all_graph_ids = [key for key in dataset if not key == "algo"]
	data_keys = [key for key in columns] #if not key == "algorithm" and not key == "graph id"]

	non_numeric_data_keys = ["algorithm", "graph id", "reduced"]
	string_data_keys = ["algorithm", "reduced"]
	might_be_string_data_keys = ["mean time", "var time", "moo", "voo", "mmo", "mvo"]

	for data in sorteddataset:
		rowstring = "\\verb+"+data["graph id"]+ "+"
		#rowstring = "\\verb+"+data["algo"] + "+ & \\verb+" + data["graph_id"] + "+"
		for data_key in data_keys:
			#print(data_key +": "+str(data[data_key]))
			if data_key not in non_numeric_data_keys and not isinstance(data[data_key], str):
				if data_key ==  "mean time":
					precision = 4
					formatstring = "${0:.4f}$"
				else:
					precision = 2
					formatstring = "${0:.2f}$"
				rowstring += " & "+formatstring.format(round(data[data_key],precision))
			elif data_key in string_data_keys+might_be_string_data_keys:
				rowstring += " & \\verb+"+data[data_key]+"+"
		texoutputstring += rowstring+"\\\\\n"
	texoutputstring += "\\end{longtable}\n"
	texoutputstring += "\\end{document}\n"

	with open(outputfilename, "w") as tex_output:
		tex_output.write(texoutputstring)
	
def write_stats_to_file(datadir, stats):
	with open(datadir+"/stats.json", 'w') as statsfile:
		json.dump(stats, statsfile, cls=meta.My_JSON_Encoder)

def load_stats_from_file(datadir):
	[path, filename] = gdo.check_filepath(datadir+"/stats.json")

	if not os.path.isdir(path):
		## TO DO: raise error
		return

	if not ".json" in filename:
		filename += ".json"

	with open(path+filename) as jsonfile:
		data = json.load(jsonfile)

	return data
	
def compute_relative_performance_distribution(setname, graph_set_id, axis="OUTPUT", algo_subset=None):
	'''
	for a set of experiments defined by a setname and a graph_set_id,
	this method computes the relative performance of all algorithms individually
	for each graph of the dataset.
	That is, for each graph of the dataset the algorithms get ordered by performance.

	args:
		setname : the name of the major graph class (ie. "general", "planar", ...)
		graph_set_id : the id of the subclass of graphs
		axis : the axis of evaluation output that should be used for evaluation, ie "OUTPUT" or "TIME"
		algo_subset : if not None, only algorithms contained in this subset will be considered

	return:
		rp : a dict that maps algorithms to lists. For each algorithm a list is constructed that contains the
		relative performance on each input graph.
		That is, if "ALGO_A" performed second best on the 15th test graph, then rp["ALGO_A"][14] = 2
	'''
	# initialize:
	datadir = "data/eval/random_"+setname+"/results"
	all_files_in_dir = os.listdir(datadir)
	files = [file for file in all_files_in_dir if ".json" in file and graph_set_id in file]
	data = {}
	files.sort()
	number_of_results = 0

	# load data:
	for algofile in files:
		filepath = datadir+"/"+algofile
		algo = get_algo_name_from_filename(algofile)
		if algo_subset == None or algo in algo_subset:
			data[algo] = load_axis_data_from_file(filepath, axis, True)
			if number_of_results == 0:
				number_of_results = len(data[algo])

	# compute average_relative_performance:
	rpd = {algo : [] for algo in data}
	#rprd = {algo : [] for algo in data}
	algos = [algo for algo in data]
	for i in range(number_of_results):
		results = {}
		for algo in data:
			results[algo] = data[algo][i]
			if results[algo] < 0:
				results[algo] += 1000000
		algoorder = sorted(algos, key=lambda a: results[a])
		j = 1
		for a_i in range(len(algos)):
			rpd[algoorder[a_i]].append(j)
			if a_i < len(algos)-1 and results[algoorder[a_i+1]] > results[algoorder[a_i]]:
				j += 1
				
		for algo in algos:
			rpd[algo][-1] = len(algos)*float(rpd[algo][-1])/j
				
	#rpr = {algo : [x/max(rpd[algo]) for x in rpd[algo]] for algo in rpd}
	return rpd

def compute_mean_relative_performance(setname, graph_set_id, axis="OUTPUT"):
	# initialize:
	datadir = "data/eval/random_"+setname+"/results"
	all_files_in_dir = os.listdir(datadir)
	files = [file for file in all_files_in_dir if ".json" in file and graph_set_id in file]
	algos = []
	
	# load data:
	for algofile in files:
		algos.append(get_algo_name_from_filename(algofile))

	rp = compute_relative_performance_distribution(setname, graph_set_id, axis)
	mrp = {algo : np.mean(rp[algo]) for algo in algos}

	return mrp