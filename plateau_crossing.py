#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
import argparse

# get the parameters from the command line:
parser = argparse.ArgumentParser()
parser.add_argument("N", type=np.float, help="Population size")
parser.add_argument("mut", type=np.float, help="mutation rate")
parser.add_argument("r", type=np.float, help="frequency of sex")
parser.add_argument("s", type=np.float, help="advantage of triple mutant")
parser.add_argument("--out", default='./', help="prefix for output files")
parser.add_argument("--tmax", type=np.float, default=1e8, help="max number of generations to run for")
parser.add_argument("--tstep", type=np.int, default=10, help="record the population state every tstep generations")
parser.add_argument("--seed", default=None, type=np.int, help="seed for random number generator")
args = parser.parse_args()

n = np.uint64(args.N)
m = args.mut
r = args.r
s = args.s
tmax = np.uint64(args.tmax)

with open(args.out + 'params.txt','w') as outfile:
	print("\n".join(["N = {:.3g}", "mu = {}", "r = {}", "s = {}", "tstep = {}", "seed = {}"]).format(n, m, r, s, args.tstep, args.seed), file=outfile)


def multinomial_robust(N, p, eps=1e-7):
	if np.all(p > eps): # no small probabilities, ordinary multinomial is safe
		return np.random.multinomial(N, p)
	else: # handle the small probabilities with Poisson draws, then do multinomial for the rest
		n = np.zeros(len(p), dtype=np.uint64)
		ismall = np.nonzero(p <= eps)[0]
		ilarge = np.nonzero(p > eps)[0]
		for i in ismall:
			n[i] = np.random.poisson(N * p[i])
		n_large = np.random.multinomial(N - np.sum(n), p[ilarge] / np.sum(p[ilarge]))
		for i, nl_i in enumerate(n_large):
			n[ilarge[i]] = nl_i
		return n 

def check_freq(f):
	if np.abs(np.sum(f)-1) > 1e-6 or np.any(f < 0) or np.any(f > 1):
		return False
	else:
		return True


genotypes = np.array([[-1,-1,-1], [1,-1,-1], [-1,1,-1], [-1,-1,1], [1,1,-1], [1,-1,1], [-1,1,1], [1,1,1]])
mutation = np.zeros((8,8))

for i in range(8):
	for j in range(8):
		if genotypes[i] @ genotypes[j] == 1:
			mutation[i,j] = m

def mendel_prob(x, y, z):
	# x and y recombine to form z:
	p = 1
	for locus in range(len(x)):
		if x[locus] == y[locus] == z[locus]:
			continue
		elif x[locus] == z[locus] or y[locus] == z[locus]:
			p *= 1/2
		else:
			return 0
	return p

recombination = np.array([[[mendel_prob(x, y, z) for z in genotypes] for y in genotypes] for x in genotypes])

fit_genotype = np.ones(8)
fit_genotype[-1] += s
freq_genotype = np.zeros(8)
freq_genotype[0] = 1.0
num_genotype = np.zeros(8, dtype=np.uint64)
num_genotype[0] = n

np.random.seed(args.seed)

with open(args.out + "trajectory.txt", 'w') as outfile:
	with open(args.out + "warnings.log", 'w') as logfile:
		for t in range(tmax):
			# recombination:
			freq_genotype += -r/2 * freq_genotype + r/2 * freq_genotype @ (freq_genotype @ recombination)
			# mutation: 
			freq_genotype += freq_genotype @ mutation - m * 3 * freq_genotype
			# selection:
			freq_genotype *= fit_genotype / (freq_genotype @ fit_genotype)
			# check that everything went ok:
			if not check_freq(freq_genotype):
				print("Warning: improper genotype frequencies ", freq_genotype)
			# sampling:
			prvs_gen = num_genotype
			num_genotype = multinomial_robust(n, freq_genotype)
			if num_genotype[-1] > 0 and np.sum(prvs_gen[4:]) == 0:
				print("Warning! Triples appear out of nothing at t={}.".format(t),"\nPrevious generation: ", prvs_gen, "\nPre-sampling frequencies: ", ' '.join(str(x) for x in freq_genotype), "\nNew generation: ", num_genotype, file=logfile)
			freq_genotype = num_genotype / n
	
			# if triples reach a frequency higher than 1/2, then they have taken over the population:
			if freq_genotype[-1] > 1/2:
				print(t, ' '.join(str(n) for n in num_genotype), file=outfile)
				break
			
			#save every tstep generations:
			if t%args.tstep == 0:
				print(t, ' '.join(str(n) for n in num_genotype), file=outfile)