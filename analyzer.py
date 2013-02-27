import numpy as np 
import scipy.io.wavfile as sciowav
import matplotlib.pyplot as plt
from pylab import *
import math
import time
import json

# Normalize db scale from 0 to 1
def normDB(arr):
	minVal = np.min(arr)
	arr = arr-minVal
	maxVal = np.max(arr)
	arr = arr/maxVal
	return arr

# Normlaize power scale from 0 to 1
def normPower(arr):
	print arr
	maxVal = np.max(arr)
	arr = arr/maxVal
	return arr

# Normalize hann window to sum to 1 to prevent scaling
# when smoothing
def normHann(hann):
	total = np.sum(hann)
	hann = hann*(1/total)
	return hann

# Extra stuff not relevant for projectdef getBarkVecs(barks,uniqueBarks,powerData):
def barkVects(powerData,uniqueBarks):
	barkVecs = []
	for bark in uniqueBarks:
	    barkVecs.append(powerData[barks == bark].mean())
	return barkVecs

# Calculate bark values for frequency bands
def bark(f):
	a = 13*np.arctan(0.00076*f)
	b = 3.5*np.arctan(np.power((f/7500),2))
	return np.floor(a+b)

# Calculate the normalization values to mimic human perception of spectrogram frequencies
def DBNorm(f):
	f = f/1000;
	a = -3.64*np.power(f,-0.8)
	b = 6.5*np.exp(-0.6*np.power((f-3.3),2))
	c = np.power(f,4)/1000
	result = a+b-c
	result[0] = -150
	return result

# Normalized FFT for human frequency preception
# Formatted for spectrogram
def intensityAdjust(data,freqs):
	DBNorms = DBNorm(freqs)
	DBNorms = np.clip(np.array(DBNorm(freqs)).reshape(-1,1),-60,maxFloat)
	data = 20*np.log10(data/60)
	data = np.clip(data,-60,maxFloat)
	return data+DBNorms

# Normalizes an FFT spectrum for human frequency preception
def FFTAdjust(data,freqs):
	DBNorms = DBNorm(freqs)
	DBNorms = np.clip(np.array(DBNorm(freqs)),-60,maxFloat)
	data = 20*np.log10(data/60)
	data = np.clip(data,-60,maxFloat)
	return data+DBNorms

# Temporal masking of the audio spectrogram to mimic human perception
# Convolves with a 0.2 sec half-hann window
def tempMask(data):
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
def segment(data):
	specVar = np.zeros(data[0,:].shape)
	for i in xrange(freqs.size):
		specVar += np.abs(np.gradient(data[i,:]))
	winSize = round(0.3/(length/bins.size))
	hannWin = np.hanning(winSize)
	specVar = np.convolve(specVar,hannWin,mode='same')
	specVarGrad = np.gradient(specVar)
	onsets = [bins[i] for i in xrange(len(specVarGrad)-1) if specVarGrad[i] > 0 and specVarGrad[i+1] < 0]
	segments = []
	for i,onset in enumerate(onsets):
		if i == 0:
			segments.append([0,onset])
		elif i == len(onsets)-1:
			segments.append([onset,bins[-1]])
		else:
			segments.append([onset,onsets[i+1]])
	return np.array(segments)

# Evaluates guassian function to find weightings for points
def evalGaussian(vals,sigma):
	num = np.exp(-(np.power(vals,2)/(2*sigma*sigma)))
	denom = np.sqrt(2*math.pi)*sigma
	return num/denom

# Computes FFT of each segment
# Shifts to equal tempermant (piano) scale
# For every key on scale, computes intensity using
# Guassian windows of the power spectrum of key width
# Folds keys down to 12 note chroma scale
# Finds max of chroma scale (after norming)
# Shifts down to 6 tracks for playing
def chromaSegments(audio,Fs,segments):
	chromaScales = []
	avgs = []
	for segment in segments:
		audioSeg = audio[segment[0]:segment[1]]
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
		chromaScale = np.zeros(12)
		for key in xrange(16,100):
			positions = keys[(keys > key-0.5) & (keys < key+0.5)]-key
			FFTVals = FFTSeg[(keys > key-0.5) & (keys < key+0.5)]
			weights = evalGaussian(positions,0.2)
			weights = normHann(weights)
			index = (key-16)%12
			chromaScale[index] += np.sum(FFTVals*weights)
		chromaScale = chromaScale/np.max(chromaScale)
		chromaScale = np.floor(np.argmax(chromaScale)/2)
		# weights = [num for num in xrange(len(chromaScale))]
		# avg = np.average(chromaScale,weights=weights)
		chromaScales.append(chromaScale)
		# avgs.append(avg)
	return chromaScales

maxFloat = sys.float_info.max
start = time.clock()
audio = sciowav.read("digitalLove.wav")
npA = audio[1][:,0]
print npA.shape
length = npA.shape[0]/44100.0
print length
NFFT = 2048 # the length of the windowing segments
Fs = audio[0] # the sampling frequency
print Fs
fig = plt.figure()
# Get spectrogram data
Pxx, freqs, bins, im = specgram(npA, NFFT=NFFT, Fs=Fs, noverlap=1536,cmap=cm.spectral)
clf()
barks = bark(freqs)
uniqueBarks = np.unique(barks)
DBData = intensityAdjust(Pxx,freqs)
powerData = np.power(10,(DBData/20))*60
powerData = tempMask(powerData)
segments = segment(powerData)
audioSegments = np.round(segments*44100) # Convert time to array semgents
keysToPlay = chromaSegments(npA,Fs,audioSegments)
trackData = []
for segment,key in zip(segments,keysToPlay):
	trackData.append((tuple(segment),key))
# The segments and tracks for a song
# Yeah, I copy and pasted at this point...
# Shows up as trackInfo in game.js
print json.dumps(trackData)
print time.clock()-start