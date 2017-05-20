"""
Copyright: Johannes Buchner (C) 2013

Modular, Pythonic Implementation of Nested Sampling
"""

import numpy
from numpy import exp, log, log10, pi
import progressbar
from adaptive_progress import AdaptiveETA
from numpy import logaddexp

def integrate_remainder(sampler, logwidth, logVolremaining, logZ):
	# logwidth remains the same now for each sample
	remainder = list(sampler.remainder())
	logV = logwidth
	L0 = remainder[-1][2]
	Ls = numpy.exp([Li - L0 for ui, xi, Li in remainder])
	Lmax = Ls[1:].sum(axis=0) + Ls[-1]
	Lmin = Ls[:-1].sum(axis=0) + Ls[0]
	logLmid = log(Ls.sum(axis=0)) + L0
	logZmid = logaddexp(logZ, logV + logLmid)
	logZup  = logaddexp(logZ, logV + log(Lmax) + L0)
	logZlo  = logaddexp(logZ, logV + log(Lmin) + L0)
	#print 'upper:', logZup, 'lower:', logZlo, 'middle:', logZmid
	logZerr = numpy.max([logZup - logZmid, logZmid - logZlo], axis=0)
	return logV + logLmid, logZerr

"""
Performs the Nested Sampling integration by calling the *sampler* multiple times
until the *tolerance* is reached, or the maximum number of likelihood evaluations
is exceeded.

:param sampler: Sampler
:param tolerance: uncertainty in log Z to compute to
:param max_samples: maximum number of likelihood evaluations (None for no limit)

@return dictionary containing the keys

  logZ, logZerr: log evidence and uncertainty, 
  samples: all obtained samples,
  weights: posterior samples: 
  	list of prior coordinates, transformed coordinates, likelihood value 
  	and weight
  information: information H
  niterations: number of nested sampling iterations
"""
def multi_nested_integrator(multi_sampler, tolerance = 0.01, max_samples=None, min_samples = 0):
	sampler = multi_sampler
	logVolremaining = 0
	logwidth = log(1 - exp(-1. / sampler.nlive_points))
	weights = [] #[-1e300, 1]]
	
	widgets = [progressbar.Counter('%f'),
		progressbar.Bar(), progressbar.Percentage(), AdaptiveETA()]
	pbar = progressbar.ProgressBar(widgets = widgets)
	
	i = 0
	ndata = multi_sampler.ndata
	running = numpy.ones(ndata, dtype=bool)
	last_logwidth = numpy.zeros(ndata)
	last_logVolremaining = numpy.zeros(ndata)
	last_remainderZ = numpy.zeros(ndata)
	last_remainderZerr = numpy.zeros(ndata)
	logZerr = numpy.zeros(ndata)
	ui, xi, Li = sampler.next()
	wi = logwidth + Li
	logZ = wi
	H = Li - logZ
	remainder_tails = [[]] * ndata
	pbar.currval = i
	pbar.maxval = sampler.nlive_points
	pbar.start()
	while True:
		i = i + 1
		logwidth = log(1 - exp(-1. / sampler.nlive_points)) + logVolremaining
		last_logwidth[running] = logwidth
		last_logVolremaining[running] = logwidth
		logVolremaining -= 1. / sampler.nlive_points
		
		# fill up, otherwise set weight to zero
		Lifull = numpy.zeros(ndata)
		Lifull[:] = -numpy.inf
		Lifull[running] = Li
		uifull = numpy.zeros((ndata, ui.shape[1]))
		uifull[running,:] = ui
		xifull = numpy.zeros((ndata, ui.shape[1]))
		xifull[running,:] = xi
		weights.append([uifull, xifull, Lifull, numpy.where(running, logwidth, -numpy.inf), running])
		
		logZerr[running] = (H[running] / sampler.nlive_points)**0.5
		
		#maxContribution = sampler.Lmax + logVolremaining
		#minContribution = Li + logVolremaining
		#midContribution = logaddexp(maxContribution, minContribution)
		#logZup  = logaddexp(maxContribution, logZ)
		#logZmid = logaddexp(midContribution, logZ)
		pbar.update(i)
		
		# expected number of iterations:
		i_final = -sampler.nlive_points * (-sampler.Lmax + log(exp(numpy.max([tolerance - logZerr[running], logZerr[running] / 100.], axis=0) + logZ[running]) - exp(logZ[running])))
		i_final = numpy.where(i_final < i+1, i+1, numpy.where(i_final > i+100000, i+100000, i_final))
		pbar.maxval = i_final.max()
		#logmaxContribution = logZup - logZ
		
		if i > max(min_samples, sampler.nlive_points): # and all(remainderZ - log(100) < logZ):
		#if i > min_samples:
			remainderZ, remainderZerr = integrate_remainder(sampler, logwidth, logVolremaining, logZ[running])
			# tolerance
			#remainderZerr[remainderZerr == 0] = 100
			last_remainderZ[running] = remainderZ
			last_remainderZerr[running] = remainderZerr
			total_error = logZerr[running] + remainderZerr
			terminating = numpy.logical_or(total_error < tolerance, remainderZerr < logZerr[running] / 10.)
			#terminating = numpy.random.uniform(size=running.sum()) < 0.1
			widgets[0] = '|%d/%d samples+%d/%d|lnZ = %.2f +- %.3f + %.3f|L=%.2f ' % (
				i + 1, pbar.maxval, sampler.nlive_points, sampler.ndraws, logaddexp(logZ[running][0], remainderZ[0]), max(logZerr[running]), max(remainderZerr), Li[0])
			if terminating.any():
				print 'terminating some:', total_error < tolerance, remainderZerr < logZerr[running] / 10.
				for j, k in enumerate(numpy.where(running)[0]):
					if terminating[j]:
						remainder_tails[k] = [[ui, xi, Li, logwidth] for ui, xi, Li in sampler.remainder(j)]
				sampler.cut_down(~terminating)
				running[running] = ~terminating
			if not running.any():
				break
			#print logZ[running][0], remainderZ[0], logZerr[running], remainderZerr, Li, logaddexp(logZ[running][0], remainderZ[0])
		else:
			widgets[0] = '|%d/%d samples+%d/%d|lnZ = %.2f +- %.3f|L=%.2f ' % (
				i + 1, pbar.maxval, sampler.nlive_points, sampler.ndraws, logZ[running][0], max(logZerr[running]), Li[0])
		print widgets[0]
		ui, xi, Li = sampler.next()
		wi = logwidth + Li
		logZnew = logaddexp(logZ[running], wi)
		H[running] = exp(wi - logZnew) * Li + exp(logZ[running] - logZnew) * (H[running] + logZ[running]) - logZnew
		logZ[running] = logZnew
	
	# not needed for integral, but for posterior samples, otherwise there
	# is a hole in the most likely parameter ranges.
	#remainderZ, remainderZerr = integrate_remainder(sampler, last_logwidth, last_logVolremaining, logZ, ~running)
	
	#weights += [[ui, xi, Li, last_logwidth, running] for ui, xi, Li in sampler.remainder()]
	all_tails = numpy.ones(ndata, dtype=bool)
	for i in range(sampler.nlive_points):
		u, x, L, logwidth = zip(*[tail[i] for tail in remainder_tails])
		weights.append([u, x, L, logwidth, all_tails])
	logZerr = logZerr + last_remainderZerr
	logZ = logaddexp(logZ, last_remainderZ)
	
	return dict(logZ=logZ, logZerr=logZerr, 
		samples=sampler.samples, weights=weights, information=H,
		niterations=i)

__all__ = [multi_nested_integrator]

