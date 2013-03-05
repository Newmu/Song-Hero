import numpy as np 
import scipy.io.wavfile as sciowav
from pylab import specgram
import math
import time
import json
import sys

class Analyzer:
	def __init__(self,filePath):
		self.data = sciowav.read(filePath)
		self.Fs = self.data[0]
		self.audio = self.data[1][:,0]
		self.length = float(self.audio.shape[0])/self.Fs
		self.powerData, self.freqs, self.bins, self.im = specgram(self.audio, NFFT=2048, Fs=self.Fs, noverlap=1536)
		self.binTime = self.length/self.bins.size
		self.barks = self.bark()
		self.uniqueBarks = np.unique(self.barks)
		self.DBData = self.specGramAdjust(powerData)
		self.powerData = self.tempMask(self.DBToPow(DBData))
		self.segments = self.getSegments()
		self.timbreSegs = self.timbreVecs()
		self.pitchSegs = self.pitchSegments()
		self.loudSegs = self.getLoudSegs(powerData,bins,binTime,segments)
		segments = self.merge()

	def segment(self):
		return self.segments
	
	# Normalize db scale from 0 to 1
	def normDB(self,arr):
		minVal = np.min(arr)
		arr = arr-minVal
		maxVal = np.max(arr)
		arr = arr/maxVal
		return arr

	# Normlaize power scale from 0 to 1
	def normPower(self,arr):
		print arr
		maxVal = np.max(arr)
		arr = arr/maxVal
		return arr

	# Normalize hann window to sum to 1 to prevent scaling
	# when smoothing
	def normHann(self,hann):
		total = np.sum(hann)
		hann = hann*(1/total)
		return hann

	# Convert list/array from decibels to power spectrum
	def DBToPow(self,db):
		db = np.array(db)
		return np.power(10,(db/20))*60

	# Convert list/array from power spectrum to decibels
	def powToDB(self,powData):
		powData = np.array(powData)
		DB = 20*np.log10(powData/60)
		return np.clip(DB,-60,sys.float_info.max)

	# Return a slice of power spectrum data
	def getSegData(self,data,seg,bins):
		start = np.where(bins==seg[0])[0]
		end = np.where(bins==seg[1])[0]
		return data[:,start:end]

	def getLoudSegs(self,powerData,bins,binTime,segments):
		loudnessFeats = []
		for seg in segments:
			segPowerData = getSegData(powerData,seg,bins)
			segLoudness = []
			for i in xrange(segPowerData.shape[1]):
				segLoudness.append(np.mean(segPowerData[:,i]))
			DBSegLoudness = powToDB(segLoudness)
			loudness = {}
			loudness['start'] = DBSegLoudness[0]
			loudness['end'] = DBSegLoudness[-1]
			loudness['max'] = np.max(DBSegLoudness)
			loudness['max_time'] = np.argmax(DBSegLoudness)*binTime
			loudnessFeats.append(loudness)
		return loudnessFeats

	# Extra stuff not relevant for project
	def timbreVecs(self,powerData,bins,segments,uniqueBarks):
		timbreVecs = []
		for seg in segments:
			segPowerData = getSegData(powerData,seg,bins)
			segTimbreVecs = []
			for i in xrange(segPowerData.shape[1]):
				timbreVec = []
				for bark in uniqueBarks:
				    timbreVec.append(segPowerData[:,i][barks == bark].mean())
				segTimbreVecs.append(timbreVec)
			timbreVecs.append(np.mean(segTimbreVecs,0))
		return powToDB(timbreVecs)

	# Calculate bark values for frequency bands
	def bark(self,f):
		a = 13*np.arctan(0.00076*f)
		b = 3.5*np.arctan(np.power((f/7500),2))
		return np.floor(a+b)

	# Calculate the normalization values to mimic human perception of spectrogram frequencies
	def DBNorm(self,f):
		f = f/1000;
		a = -3.64*np.power(f,-0.8)
		b = 6.5*np.exp(-0.6*np.power((f-3.3),2))
		c = np.power(f,4)/1000
		result = a+b-c
		result[0] = -150
		return result

	def specGramAdjust(self,data,freqs):
		DBNorms = DBNorm(freqs)
		DBNorms = np.clip(np.array(DBNorm(freqs).reshape(-1,1)),-60,sys.float_info.max)
		data = powToDB(data)
		return data+DBNorms

	# Normalizes an FFT spectrum for human frequency preception
	def FFTAdjust(self,data,freqs):
		DBNorms = DBNorm(freqs)
		DBNorms = np.clip(np.array(DBNorm(freqs)),-60,sys.float_info.max)
		data = powToDB(data)
		return data+DBNorms

	# Temporal masking of the audio spectrogram to mimic human perception
	# Convolves with a 0.2 sec half-hann window
	def tempMask(self,data,freqs):
		dataMasked = np.zeros(data.shape)
		for i in xrange(freqs.size):
			winSize = round(0.4/(length/bins.size))
			hann = np.hanning(winSize)
			halfPoint = np.argmax(hann)
			hann = hann[halfPoint:]
			hann = normHann(hann)
			dataMasked[i,:] = np.convolve(data[i,:],hann,mode='same')
		return dataMasked

	# Segments the audio into subsections for each note or spectral change
	# Calculates spectral varience and smooths result with hann win
	# Detects peaks in spectral varience as segments
	def getSegments(self,data):
		specVar = np.zeros(data[0,:].shape)
		for i in xrange(freqs.size):
			specVar += np.abs(np.gradient(data[i,:]))
		winSize = round(0.15/(length/bins.size))
		hannWin = np.hanning(winSize)
		specVar = np.convolve(specVar,hannWin,mode='same')
		specVarGrad = np.gradient(specVar)
		onsets = [bins[i] for i in xrange(len(specVarGrad)-1) if specVarGrad[i] > 0 and specVarGrad[i+1] < 0]
		segments = []
		for i,onset in enumerate(onsets):
			if i == 0:
				segments.append([bins[0],onset])
			elif i == len(onsets)-1:
				segments.append([onset,bins[-1]])
			else:
				segments.append([onset,onsets[i+1]])
		return np.array(segments)

	# Evaluates guassian function to find weightings for points
	def evalGaussian(self,vals,sigma):
		num = np.exp(-(np.power(vals,2)/(2*sigma*sigma)))
		denom = np.sqrt(2*math.pi)*sigma
		return num/denom

	# Computes FFT of each segment
	# Shifts to equal tempermant (piano) scale
	# For every key on scale, computes intensity using
	# Guassian windows of the power spectrum of key width
	# Folds keys down to 12 note pitch scale
	# Finds max of pitch scale (after norming)
	# Shifts down to 6 tracks for playing
	def pitchSegments(self,audio,Fs,segments):
		segments = np.round(segments*44100)
		pitchScales = []
		avgs = []
		for seg in segments:
			audioSeg = audio[seg[0]:seg[1]]
			n = len(audioSeg)+8096
			FFTSeg = 2*np.abs(np.fft.rfft(audioSeg,n))
			freqs = np.fft.fftfreq(n,float(1)/Fs)
			halfPoint = np.argmin(freqs)
			freqs = freqs[:halfPoint+1]
			FFTSeg = FFTAdjust(FFTSeg,freqs)
			FFTSeg = np.power(10,(FFTSeg/20))*60
			FFTSeg = FFTSeg[1:-1]
			keys = 12*np.log2(freqs/440)+49
			keys = keys[1:-1]
			avg = np.average(keys,weights=FFTSeg)
			pitchScale = np.zeros(12)
			for key in xrange(16,100):
				positions = keys[(keys > key-0.5) & (keys < key+0.5)]-key
				FFTVals = FFTSeg[(keys > key-0.5) & (keys < key+0.5)]
				weights = evalGaussian(positions,0.2)
				weights = normHann(weights)
				index = (key-16)%12
				pitchScale[index] += np.sum(FFTVals*weights)
			pitchScale = pitchScale/np.max(pitchScale)
			pitchScales.append(pitchScale)
		return pitchScales

	def merge(self,segs,timbres,pitches,loudness):
		segments = []
		for i in xrange(len(segs)):
			seg = {}
			seg['start'] = segs[i][0]
			seg['end'] = segs[i][1]
			seg['duration'] = segs[i][1]-segs[i][0]
			seg['loudness_start'] = loudness[i]['start']
			seg['loudness_end'] = loudness[i]['end']
			seg['loudness_max'] = loudness[i]['max']
			seg['loudness_max_time'] = loudness[i]['max_time']
			seg['pitches'] = list(pitches[i])
			seg['timbres'] = list(timbres[i])
			segments.append(seg)
		return segments

analyzer = Analyzer('digitalLove.wav')
print analyzer.segment()