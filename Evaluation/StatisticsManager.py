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

def load_axis_data_from_file(filename, axis, keep_nulls=False):
	with open(filename) as jsonfile:
		this_file_data = json.load(jsonfile)

	if axis=="OUTPUT":
		data = [d["output"] for d in this_file_data]
	elif axis=="TIME":
		data = [d["running_time"] for d in this_file_data if d["running_time"]>0]

	if not keep_nulls:
		return [d for d in data if d>0]
	else:
		return data

def get_algo_name_from_filename(filename):
	algo_parts = re.split('_',filename)
	algo_name = algo_parts[2]
	b_id = 3
	if algo_parts[3][0] == "R":
		algo_name += "_"+algo_parts[3]
		b_id += 1
	if algo_parts[b_id] == "B":
		algo_name += "_B"
	return algo_name

def compute_relative_performance(setname, graph_set_id, axis="OUTPUT"):
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
		data[algo] = load_axis_data_from_file(filepath, axis, True)
		if number_of_results == 0:
			number_of_results = len(data[algo])

	# compute average_relative_performance:
	rp = {algo : [] for algo in data}
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
			rp[algoorder[a_i]].append(j)
			if a_i < len(algos)-1 and results[algoorder[a_i+1]] > results[algoorder[a_i]]:
				j += 1

	return rp

def compute_mean_relative_performance(setname, graph_set_id, axis="OUTPUT"):
	# initialize:
	datadir = "data/eval/random_"+setname+"/results"
	all_files_in_dir = os.listdir(datadir)
	files = [file for file in all_files_in_dir if ".json" in file and graph_set_id in file]
	algos = []
	
	# load data:
	for algofile in files:
		algos.append(get_algo_name_from_filename(algofile))

	rp = compute_relative_performance(setname, graph_set_id, axis)
	mrp = {algo : np.mean(rp[algo]) for algo in algos}

	return mrp

def make_boxplot(data, setname, graph_set_id, ylabel, savedir=None, filename_suffix=None):
	# initialize:
	datadir = "data/eval/random_"+setname+"/results"
	all_files_in_dir = os.listdir(datadir)
	files = [file for file in all_files_in_dir if ".json" in file and graph_set_id in file]
	labels = []
	files.sort()

	# get labels:
	for file in files:
		filepath = datadir+"/"+file
		results_label = get_algo_name_from_filename(file)
		labels.append(results_label)

	# create plot:
	fig, ax1 = plt.subplots(figsize=(len(data), 6))
	#fig.canvas.set_window_title('A Boxplot Example')
	fig.subplots_adjust(bottom=0.3)

	ax1.set_xlabel('Algorithm')
	ax1.set_ylabel(ylabel)
	
	bp = ax1.boxplot(data, notch=0, sym='+', vert=1, whis=1.5)
	plt.setp(bp['boxes'], color='black')
	ax1.set_xticklabels(labels)
	for tick in ax1.get_xticklabels():
		tick.set_rotation(90)
	if savedir == None:
		plt.show()
	elif filename_suffix == None:
		plt.savefig(savedir+"/boxplots_"+graph_set_id+".png")
	else:
		plt.savefig(savedir+"/boxplots_"+graph_set_id+"_"+filename_suffix+".png")
	plt.close()

def make_boxplot_set(setname, graph_set_id, axis="OUTPUT", type="ABSOLUTE", savedir=None):
	if type == "ABSOLUTE":
		# initialize:
		datadir = "data/eval/random_"+setname+"/results"
		all_files_in_dir = os.listdir(datadir)
		files = [file for file in all_files_in_dir if ".json" in file and graph_set_id in file]
		data = []
		files.sort()
	
		# load data:
		for file in files:
			filepath = datadir+"/"+file
			data.append(load_axis_data_from_file(filepath, axis))

	elif type == "RP":
		database = compute_relative_performance(setname, graph_set_id, axis)
		data = [database[key] for key in database]
	filename_suffix = axis+"_"+type
			
	make_boxplot(data, setname, graph_set_id, axis+" ("+type+")", savedir, filename_suffix)

def make_boxplots_all(setname, axis="OUTPUT", type="ABSOLUTE"):
	basedir = "data/eval/random_"+setname
	graphdir = basedir+"/input"
	resultdir = basedir+"/results"
	outputdir = basedir+"/plots"
	if not os.path.exists(outputdir):
		os.mkdir(outputdir)

	all_graph_set_ids = []
	for filename in os.listdir(graphdir):
		all_graph_set_ids.append(re.split(r'\.',filename)[0])

	for graph_set_id in all_graph_set_ids:
		make_boxplot_set(setname, graph_set_id, axis, type, outputdir)

def plot_mean_performance_by_density(setname, n, axis="OUTPUT", type="ABSOLUTE", savedir=None):
	basedir = "data/eval/random_"+setname
	graphdir = basedir+"/input"
	resultdir = basedir+"/results"
	
	all_graph_set_ids_master = {}
	for filename in os.listdir(graphdir):
		if "n"+str(n) in filename:
			graph_set_id = re.split(r'\.',filename)[0]
			graph_set_id_parts = re.split('_', graph_set_id)
			if len(graph_set_id_parts) > 3:
				if graph_set_id_parts[3] not in all_graph_set_ids_master:
					all_graph_set_ids_master[graph_set_id_parts[3]] = []
				all_graph_set_ids_master[graph_set_id_parts[3]].append(graph_set_id)
			else:
				if '' not in all_graph_set_ids_master:
					all_graph_set_ids_master[''] = []
				all_graph_set_ids_master[''].append(graph_set_id)
	
	for graph_set_key in all_graph_set_ids_master:
		files = []
		
		all_graph_set_ids = all_graph_set_ids_master[graph_set_key]
		filename_suffix = ''
		if not graph_set_key == '':
			filename_suffix += graph_set_key+"_"
			
		for graph_set_id in all_graph_set_ids:
			files += [file for file in os.listdir(resultdir) if ".json" in file and graph_set_id in file]
	
		database = {}
		if type == "ABSOLUTE":
			for file in files:
				algo = get_algo_name_from_filename(file)
				evaldata = em.load_evaldata_from_json(basedir, file)
				avg_m = np.mean([data.m for data in evaldata])
				if axis == "OUTPUT":
					data = [data.output for data in evaldata if data.output >= 0]
				elif axis == "TIME":
					data = [data.running_time for data in evaldata if data.output >= 0]
				if algo not in database:
					database[algo] = {}
				database[algo][avg_m] = np.mean(data)
		
		elif type == "RP":
			for graph_set_id in all_graph_set_ids:
				mrt = compute_mean_relative_performance(setname, graph_set_id, axis)
				examplefile = [file for file in os.listdir(resultdir) if ".json" in file and graph_set_id in file][0]
				evaldata = em.load_evaldata_from_json(basedir, examplefile)
				avg_m = np.mean([data.m for data in evaldata])
				for algo in mrt:
					if algo not in database:
						database[algo] = {}
					database[algo][avg_m] = mrt[algo]
		
		fig, ax = plt.subplots()
		legenditems = {}
		for algo in database:
			basealgo = re.split('_', algo)[0]
			linestyle = '-'
			if "_B" in algo:
				if "_R" in algo:
					linestyle = '-.'
				else:
					linestyle = ':'
			elif "_R" in algo:
				linestyle = '--'
			
			m = sorted([avg_m for avg_m in database[algo]])
			data = [database[algo][avg_m] for avg_m in m]
			line = ax.plot(m, data, label=algo, linewidth=0.5, linestyle=linestyle, color=gs.PLT_ALGO_COLORS[basealgo])
			if basealgo not in legenditems:
				legenditems[basealgo] = mlines.Line2D([],[], color=gs.PLT_ALGO_COLORS[basealgo], label=basealgo) 
		
		ax.set_xlabel('number of edges (i.e. density)')
		ax.set_ylabel(axis+" ("+type+")")
		legend = ax.legend(handles=[legenditems[a] for a in legenditems], bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
		
		if savedir == None:
			plt.show()
		else:
			filename_suffix += axis+"_"+type
			filename = savedir+"/plots_by_density_"+setname+"_n"+str(n)+"_"+filename_suffix+".png"
			print (filename)
			plt.savefig(filename, dpi=500, bbox_extra_artists=(legend,), bbox_inches='tight')
		plt.close()
		
def make_performance_plots_all(setname, axis="OUTPUT", type="ABSOLUTE"):
	basedir = "data/eval/random_"+setname
	outputdir = basedir+"/plots"
	if not os.path.exists(outputdir):
		os.mkdir(outputdir)

	for n in [20, 40, 60, 80, 100]:
		plot_mean_performance_by_density(setname, n, axis, type, savedir=outputdir)