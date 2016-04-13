
import numpy as np
from scipy.signal import fftconvolve
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt
import os, glob, optparse, time

##=============================================================================
def main():
	"""
	"""
	me = "SymPlot.main: "
	t0 = time.time()

	## Options
	parser = optparse.OptionParser()
	parser.add_option('-s','--show',
		dest="showfig", default=False, action="store_true")
	parser.add_option('-a','--plotall',
		dest="plotall", default=False, action="store_true")
	parser.add_option('-v','--verbose',
		dest="verbose", default=False, action="store_true")
	opt, args = parser.parse_args()
	showfig = opt.showfig
	plotall = opt.plotall
	verbose = opt.verbose

	if os.path.isfile(args[0]):
		plot_time(args[0], verbose)
	elif os.path.isdir(args[0]) and plotall:
		showfig = False
		plot_time_all(args[0], verbose)
	elif os.path.isdir(args[0]):
		plot_delta(args[0], verbose)
	else:
		raise IOError(me+"Input not a file or directory.")

	print me+"Execution",round(time.time()-t0,2),"seconds."
	if showfig: plt.show()
	
	return


##=============================================================================
def plot_time(datafile, vb):
	"""
	"""
	me = "SymPlot.plot_time: "

	plotfile = datafile[:-4]+".png"
	Delta = get_pars(datafile)
	k = get_headinfo(datafile)

	npts = 500
	data = np.loadtxt(datafile, skiprows=10, unpack=True)
	data = data[:, ::int(data.shape[1]/npts)]

	t, ent, work, trans_C, trans_I = data[[0,5,6,8,9]]
	N = int(data[[1,2,3,4],0].sum())
	del data

	ent /= N*np.log(2)
	Dent, Sssid = flatline(ent)
	tSS = t[Sssid]

	##-------------------------------------------------------------------------
	## Find average work rate and final entropy value
	## Assuming entropy is flat and work is linear

	# S_fin = np.mean(ent[Sssid:])
	# Wdot_evo = np.mean(work[:Sssid-int(npts/20)])/t[Sssid]
	# Wdot_SS = np.mean(work[Sssid:]-work[Sssid])/(t[-1]-t[Sssid])
	# annotext = "$\Delta S = %.2e$ \n $\dot W_{evo} = %.2e$ \n $\dot W_{SS} = %.2e$ \n $t_{SS} =  %.2e$"\
		# % (S_fin, Wdot_evo, Wdot_SS, t[Sssid])

	##-------------------------------------------------------------------------
	## Plotting

	plt.clf()

	plt.plot(t, ent, "b-", label="$S / N\ln2$")
	plt.plot(t, -work/work[-1], "g-", label="$W / W(tmax)$")

	## Theory
	plt.axhline(SSS_theo(Delta, k),   c="b",ls=":",lw=2, label="$S$ prediction")
	plt.axvline(SSt_theo(Delta, k)*N, c="r",ls=":",lw=2, label="$\\tau$ prediction")
	# plt.plot(t,-1+(t[-1]-t)*SSW_theo(Delta, k)/N*4, c="g",ls=":",lw=2,label="$\\dot W_{\\rm SS}$ prediction")
	# plt.plot(t,-1+(1-t/t[-1]), c="g",ls=":",lw=2,label="$\\dot W_{\\rm SS}$ prediction")
	plt.plot(t,-t/t[-1]+SSW_theo(Delta, k)*t[-1]/N*(t/t[-1]-1), c="g",ls=":",lw=2,label="$\\dot W_{\\rm SS}$ prediction")
	
	plt.axvline(tSS, c="k")
	plt.axvspan(t[0],tSS,  color="y",alpha=0.05)
	plt.axvspan(tSS,t[-1], color="g",alpha=0.05)

	plt.xlim(left=0.0,right=t[-1])
	plt.ylim([-1.1,0.1])
	plt.xlabel("$t$")
	plt.title("$\Delta=$"+str(Delta))
	plt.legend()
	# plt.annotate(annotext,xy=(0.15,0.2),xycoords="figure fraction",fontsize=16)
	plt.grid()

	plt.savefig(plotfile)
	if vb:	print me+"Plot saved to",plotfile

	return

##=============================================================================

def plot_time_all(dirpath, vb):
	for datafile in glob.glob(dirpath+"/*.txt"):
		plot_time(datafile, vb)
	return

##=============================================================================

def plot_delta(dirpath, vb):
	"""
	"""
	me = "SymPlot.plot_delta: "
	t0 = time.time()
		
	## Outfile name and number of points to plot
	plotfile = dirpath+"/DeltaPlots.png"
	npts = 500

	##-------------------------------------------------------------------------

	filelist = np.sort(glob.glob(dirpath+"/*.txt"))
	numfiles = len(filelist)
	if numfiles%2 != 0:
		raise IOError(me+"Expecting an even number of files (Hopfield and Notfield).")
		
	## Separate by Hop and Not
	hoplist = filelist[:numfiles/2]
	notlist = filelist[numfiles/2:]
	
	## Initialise arrays
	Delta = np.zeros(numfiles)
	S_fin = np.zeros(numfiles)
	t_SS = np.zeros(numfiles)
	t_SS_th = np.zeros(numfiles)
	W_srt = np.zeros(numfiles)
	Wdot_SS = np.zeros(numfiles)
	ERR = np.zeros(numfiles)
	
	## Get data from all files
	for i in range(numfiles):
	
		Delta[i] = get_pars(filelist[i])
		k = get_headinfo(filelist[i])
	
		data = np.loadtxt(filelist[i], skiprows=10, unpack=True)
		## Prune
		data = data[:, ::int(data.shape[1]/npts)]
		
		## Read relevant columns
		t, ent, work, trans_C, trans_I, err = data[[0,5,6,8,9,12]]
		N = int(data[[1,2,3,4],0].sum())
		del data
		
		## Normalise ent and find SS index
		ent /= N*np.log(2)	
		Dent, SSidx = flatline(ent, N, Delta, kerfrac=100)
		tSS = t[SSidx]
		
		## Collect data
		## Assume entropy is flat and work is linear
		S_fin[i] = np.mean(ent[SSidx:])
		t_SS[i] = tSS
		W_srt[i] = work[SSidx]
		Wdot_SS[i] = np.mean(work[SSidx:]-work[SSidx])/(t[-1]-tSS)
		ERR[i] = err.mean()
	
		## Construct prediction arrays
		t_SS_th[i] = SSt_theo(D,k)
		
		
	## ----------------------------------------------------
	
	## Separate into H and N
	newshape = (2,numfiles/2)
	Delta = Delta.reshape(newshape)
	S_fin = S_fin.reshape(newshape)
	t_SS = t_SS.reshape(newshape)
	t_SS_th = t_SS_th.reshape(newshape)
	W_srt = W_srt.reshape(newshape)
	Wdot_SS  = Wdot_SS.reshape(newshape)
	ERR = ERR.reshape(newshape)
	
	## Sort by Delta
	sortind = np.argsort(Delta)
	Delta = Delta[:,sortind[0]]
	try:
		assert np.all(Delta[0]==Delta[1])
	except AssertionError:
		raise IOError(me+"Check files.\n"+filelist.tostring())
	S_fin = S_fin[:,sortind[0]]
	t_SS = t_SS[:,sortind[0]]
	t_SS_th = t_SS_th[:,sortind[0]]
	W_srt = W_srt[:,sortind[0]]
	Wdot_SS = Wdot_SS[:,sortind[0]]
	ERR = ERR[:,sortind[0]]

	## ----------------------------------------------------
	
	## Get k values, assuming the same for all files in directory
	k = [get_headinfo(filelist[0]),get_headinfo(filelist[numfiles/2])]
	
	if verbose: print me+"Data extraction and calculations:",round(time.time()-t0,2),"seconds."
	
	##-------------------------------------------------------------------------
	## Plotting
	
	fsl = 10
	colour = ["b","r","m"]
	label = ["Hopfield","Notfield"]
	D_th = np.linspace(np.min(Delta),np.max(Delta),len(Delta)*20)
	
	fitxp = [0,0]
	
	## SORTING ERROR RATE RATIO
	
	plt.figure("ERR"); ax = plt.gca()
	plotfile = dirpath+"/DeltaPlot_0_ERR.png"
	plt.subplot(111)
	for i in [0,1]:
		fit = fit_SS(ERR_theo, Delta[i], ERR[i]); fitxp[i]=round(fit[2],2)
		ax.plot(Delta[i], ERR[i], colour[i]+"o", label=label[i])
		ax.plot(Delta, Delta**(-fitxp[i]), colour[i]+":", label = "$\Delta^{-"+str(fitxp[i])+"}$")
		ax.plot(Delta, Delta**(-2+i), colour[i]+"--", label = "$\Delta^{-"+str(-2+i)+"}$")
	plt.xlim(left=1.0)
	plt.ylim(top=1.0)
	plt.xlabel("$\\Delta$")
	plt.grid()
	plt.legend(loc="upper right", fontsize=fsl)
	plt.savefig(plotfile); print me+"Plot saved to",plotfile
	
	## SS ENTROPY
	
	plt.figure("SSS"); ax = plt.gca()
	plotfile = dirpath+"/DeltaPlot_1_SSS.png"
	for i in [0,1]:
		ax.plot(Delta[i], S_fin[i], colour[i]+"o", label=label[i])
		ax.plot(D_th, SSS_theo(D_th**(2-i)), colour[i]+"--",\
			label="Optimal")
		ax.plot(fit[0],fit[1], colour[i]+":", label="Fit ("+str(fitxp[i])+")")
	ax.set_xlim(left=1.0)
	ax.set_xlabel("$\\Delta$")
	ax.set_ylabel("$\Delta S_{\mathrm{SS}} / N\ln2$")
	plt.grid()
	plt.legend(loc="upper right", fontsize=fsl)
	plt.savefig(plotfile); print me+"Plot saved to",plotfile
	
	## SS ENTROPY H/N
	
	plt.figure("SSSR"); ax = plt.gca()
	plotfile = dirpath+"/DeltaPlot_2_SSSR.png"
	S_fin_ratio = (S_fin[0]+1)/(S_fin[1]+1)
	S_fin_th_ratio = (SSS_theo(D_th**(2)+1))/(SSS_theo(D_th)+1)	
	ax.plot(Delta[0], S_fin_ratio, colour[2]+"o")
	# plt.plot(D_th, S_fin_th_ratio, colour[2]+"--",	label="Optimal")
	## SORT OUT FIT
	ax.set_xlim(left=1.0)
	ax.set_xlabel("$\\Delta$")
	ax.set_ylabel("$\Delta S_{\mathrm{SS}} / N\ln2 + 1$ ratio: H/N")
	plt.grid()
	plt.savefig(plotfile); print me+"Plot saved to",plotfile
	
	## TIME TO REACH STEADY STATE
	
	plt.figure("tSS"); ax = plt.gca()
	plotfile = dirpath+"/DeltaPlot_3_tSS.png"
	plt.subplot(111)
	for i in [0,1]:
		ax.plot(Delta[i], t_SS[i], colour[i]+"o", label=label[i])
		ax.plot(Delta[i,1:], N*t_SS_th[i,1:], colour[i]+"--", label="Theory")
	ax.set_xlim(left=1.0)
	ax.set_xlabel("$\\Delta$")
	ax.set_ylabel("$t_{\mathrm{SS}}$")
	ax.yaxis.major.formatter.set_powerlimits((0,0)) 
	plt.grid()
	plt.legend(loc="best", fontsize=fsl)
	plt.savefig(plotfile); print me+"Plot saved to",plotfile
	
	## TOTAL WORK TO SORT
	
	plt.figure("Wsort"); ax = plt.gca()
	plotfile = dirpath+"/DeltaPlot_4_Wsort.png"
	plt.subplot(111)
	for i in [0,1]:
		ax.plot(Delta[i,1:], W_srt[i,1:], colour[i]+"o", label=label[i])
	ax.set_xlim(left=1.0)
	ax.set_xlabel("$\\Delta$")
	ax.set_ylabel("$W_{\mathrm{total}}$ for sorting")
	ax.yaxis.major.formatter.set_powerlimits((0,0)) 
	plt.grid()
	plt.legend(loc="lower right", fontsize=fsl)
	plt.savefig(plotfile); print me+"Plot saved to",plotfile
	
	## SS WORK RATE
	
	plt.figure("Wdot"); ax = plt.gca()
	plotfile = dirpath+"/DeltaPlot_5_Wdot.png"
	plt.subplot(111)
	for i in [0,1]:
		ax.plot(Delta[i], Wdot_SS[i], colour[i]+"o", label=label[i])
		ax.plot(D_th, -SSW_theo(D_th,k[i],2-i), colour[i]+"--",\
			label="Theory")
	ax.set_xlim(left=1.0)
	ax.set_xlabel("$\\Delta$")
	ax.set_ylabel("$\dot W_{\mathrm{SS}}$")
	ax.yaxis.major.formatter.set_powerlimits((0,0)) 
	plt.grid()
	plt.legend(loc="lower right", fontsize=fsl)
	plt.savefig(plotfile); print me+"Plot saved to",plotfile
	
	##
	
	
	print me+"Execution",round(time.time()-t0,2),"seconds."
	
	return



##=============================================================================
##=============================================================================

def flatline(y):
	sslvl = np.mean(y[y.size/2:])
	win = y.size/20
	y_conv = fftconvolve(y,np.ones(win)/win,mode="same")
	for id, el in enumerate(y_conv-sslvl):
		if el<0.01: break
	return (y_conv, id)

##=============================================================================

def SSS_theo(D, k):
	"""
	Prediction for the SS entropy in equilibrium.
	"""
	a1b = k["A1B1"]
	ba1 = k["B1A1"]
	ca1 = k["C1A1"]
	cb  = k["C1B1"]
	num = ca1*cb + ba1*(ca1+cb) + ca1*ca1*D
	den = ba1*ca1+ba1*cb+ca1*cb + (2*ca1*ca1+ba1*cb+ca1*cb)*D + ba1*ca1*D*D
	A1SS = num/den
	return -1.0 - ( A1SS*np.log(A1SS) + (1-A1SS)*np.log(1-A1SS) ) / np.log(2)


def SSW_theo(D, k):
	"""
	Prediction for the SS work RATE.
	"""
	a1b = k["A1B1"]
	ba1 = k["B1A1"]
	ca1 = k["C1A1"]
	cb  = k["C1B1"]
	num = a1b*ca1*(ca1+2*cb) + a1b*ca1*ca1*D
	den = a1b*ca1+ba1*ca1+2*a1b*cb+ba1*cb+ca1*cb + (a1b*ca1+2*ca1*ca1+ba1*cb+ca1*cb)*D + ba1*ca1*D*D
	return num/den

def SSt_theo(D, k):
	"""
	Predction for time to reach SS.
	"""
	a1b = k["A1B1"]
	ba1 = k["B1A1"]
	ca1 = k["C1A1"]
	cb  = k["C1B1"]
	num = a1b*ba1*ca1*ca1 + ba1*ba1*ca1*ca1 + 3*a1b*ba1*ca1*cb + 2*ba1*ba1*ca1*cb + \
			a1b*ca1*ca1*cb + 2*ba1*ca1*ca1*cb + 2*a1b*ba1*cb*cb + ba1*ba1*cb*cb + \
			2*a1b*ca1*cb*cb + 2*ba1*ca1*cb*cb + ca1*ca1*cb*cb + \
			\
			(a1b*ba1*ba1*ca1 + ba1*ba1*ba1*ca1 + a1b*ba1*ca1*ca1 + a1b*ca1*ca1*ca1 + \
			3*ba1*ca1*ca1*ca1 + 2*a1b*ba1*ba1*cb + ba1*ba1*ba1*cb + 2*a1b*ba1*ca1*cb + \
			3*ba1*ba1*ca1*cb + 4*a1b*ca1*ca1*cb + 5*ba1*ca1*ca1*cb + 3*ca1*ca1*ca1*cb + \
			2*a1b*ba1*cb*cb + 2*ba1*ba1*cb*cb + 2*a1b*ca1*cb*cb + 4*ba1*ca1*cb*cb + \
			2*ca1*ca1*cb*cb) * D + \
			\
			(a1b*ba1*ba1*ca1 + a1b*ba1*ca1*ca1 + 4*ba1*ba1*ca1*ca1 + a1b*ca1*ca1*ca1 + \
			2*ca1*ca1*ca1*ca1 + ba1*ba1*ba1*cb + 3*a1b*ba1*ca1*cb + 3*ba1*ba1*ca1*cb + \
			a1b*ca1*ca1*cb + 5*ba1*ca1*ca1*cb + 3*ca1*ca1*ca1*cb + ba1*ba1*cb*cb + \
			2*ba1*ca1*cb*cb + ca1*ca1*cb*cb) * D*D + \
			\
			(ba1*ba1*ba1*ca1 + a1b*ba1*ca1*ca1 + 3*ba1*ca1*ca1*ca1 + 2*ba1*ba1*ca1*cb + \
			2*ba1*ca1*ca1*cb) * D*D*D + \
			\
			ba1*ba1*ca1*ca1 * D*D*D*D
	##
	den = a1b*(ba1*ba1*ca1*ca1 + 2*ba1*ba1*ca1*cb + 2*ba1*ca1*ca1*cb + ba1*ba1*cb*cb + 
			2*ba1*ca1*cb*cb + ca1*ca1*cb*cb) + \
			\
			a1b*(4*ba1*ca1*ca1*ca1 + 2*ba1*ba1*ca1*cb + 6*ba1*ca1*ca1*cb + 4*ca1*ca1*ca1*cb + 
			2*ba1*ba1*cb*cb + 4*ba1*ca1*cb*cb + 2*ca1*ca1*cb*cb) * D + \
			\
			a1b*(2*ba1*ba1*ca1*ca1 + 4*ca1*ca1*ca1*ca1 + 2*ba1*ba1*ca1*cb + 6*ba1*ca1*ca1*cb + 
			4*ca1*ca1*ca1*cb + ba1*ba1*cb*cb + 2*ba1*ca1*cb*cb + ca1*ca1*cb*cb) * D*D + \
			\
			a1b*(4*ba1*ca1*ca1*ca1 + 2*ba1*ba1*ca1*cb + 2*ba1*ca1*ca1*cb) * D*D*D + \
			\
			a1b*ba1*ba1*ca1*ca1 * D*D*D*D
	##
	return num/den

##=============================================================================

def get_pars(filename):
	start = filename.find("field_") + 6
	Delta = float(filename[start:filename.find("_",start)])
	return Delta

def read_header(datafile):
	"""
	Read header info from datafile.
	"""
	head = []
	f = open(datafile,'r')
	for i,line in enumerate(f):
		if i is 10: break
		head += [line]
	f.close()
	return head

def get_headinfo(datafile):
	"""
	Hard-coded function to extract initial number and rates from header string.
	There is a bug here in the parsing -- sometimes misses an entry.
	"""
	head = read_header(datafile)
	k_labels = [label.rstrip() for label in head[3].split("\t")] + [label.rstrip() for label in head[6].split("\t")]
	k_values = np.concatenate([np.fromstring(head[4],dtype=float,sep="\t"),
		np.fromstring(head[7],dtype=float,sep="\t")])
	# k_dict = dict((label,k_values[i]) for i,label in enumerate(k_labels))
	return dict(zip(k_labels,k_values))
	
	
##=============================================================================
	
def fit_SS(func,x,y):
	"""
	Make a power-law fit to points y(x).
	Returns new x and y coordinates on finer grid.
	"""
	fitfunc = lambda x,nu: func(x,nu)
	popt, pcov = curve_fit(fitfunc, x, y)
	X = np.linspace(np.min(x),np.max(x),5*x.size)
	return X, fitfunc(X, *popt), popt[0]

def ERR_theo(D,nu):
	return D**nu

##=============================================================================
##=============================================================================
if __name__=="__main__":
	main()