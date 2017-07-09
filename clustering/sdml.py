from __future__ import absolute_import
import numpy as np
import numpy
from numpy import exp
import scipy.linalg

class IdentityMetric(object):
	"""
	Input is output.
	"""
	def fit(self, x):
		pass
	def transform(self, x):
		return x
	def untransform(self, y):
		return y
	def __eq__(self, other): 
		return self.__dict__ == other.__dict__

class SimpleScaling(object):
	"""
	Whitens by subtracting the mean and scaling by the 
	standard deviation of each axis.
	"""
	def __init__(self, verbose=False):
		self.verbose = verbose

	def fit(self, X, W=None):
		self.mean = numpy.mean(X, axis=0)
		X = X - self.mean
		self.scale = numpy.std(X, axis=0)
		if self.verbose: 'Scaling metric:', self.scale
	def transform(self, x):
		return (x - self.mean) / self.scale
	
	def untransform(self, y):
		return y * self.scale + self.mean

	def __eq__(self, other): 
		return self.__dict__ == other.__dict__

class TruncatedScaling(object):
	"""
	Whitens by subtracting the mean and scaling by the 
	standard deviation of each axis. The scaling is discretized on 
	a log axis onto integers.
	"""
	def __init__(self, verbose=False):
		self.verbose = verbose
	def fit(self, X, W=None):
		self.mean = numpy.mean(X, axis=0)
		X = X - self.mean
		#scale = numpy.max(X, axis=0) - numpy.min(X, axis=0)
		scale = numpy.std(X, axis=0)
		scalemax = scale.max() * 1.001
		scalemin = scale.min()
		# round onto discrete log scale to avoid random walk
		logscale = (-numpy.log2(scale / scalemax)).astype(int)
		self.scale = 2**(logscale.astype(float))
		#print 'Scaling metric:', self.scale, '(from', scale, ')'
		if self.verbose: 'Discretized scaling metric:\n', logscale
	
	def transform(self, x):
		return (x - self.mean) / self.scale
	
	def untransform(self, y):
		return y * self.scale + self.mean

	def __eq__(self, other): 
		return self.__dict__ == other.__dict__
