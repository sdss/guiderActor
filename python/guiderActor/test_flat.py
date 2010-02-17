import os
import os.path
import re

import matplotlib
matplotlib.use('Agg')

from gimg.guiderImage import *
from gimg.guiderImagePlots import *
from YPF import *

from tests import getGprobes, ducky

#class TestGuiderImageAnalysis(GuiderImageAnalysis):
#pass

if __name__ == '__main__':
	os.environ['GUIDERACTOR_DIR'] = '..'
	
	GI = GuiderImageAnalysis(None)
	GI.setOutputDir('test-outputs')

	fiberinfofn = '../etc/gcamFiberInfo.par'

	testInputs = [
		(55243,    1,    7, 10, 'plPlugMapM-3650-55242-01.par'),
		(55243,    2,    7, 10, 'plPlugMapM-3650-55242-01.par'),
		(55243,    5,    7, 10, 'plPlugMapM-3650-55242-01.par'),
		(55243,    6,    7, 10, 'plPlugMapM-3650-55242-01.par'),
		(55243,   85,    7, 10, 'plPlugMapM-3650-55242-01.par'),
		(55243,   86,   87, 12, 'plPlugMapM-3681-55242-01.par'),
		(55243,  288,   87, 12, 'plPlugMapM-3681-55242-01.par'),
		(55243,  289,  290, 13, 'plPlugMapM-3781-55241-02.par'),
		(55243,  469,  290, 13, 'plPlugMapM-3781-55241-02.par'),
		(55243,  470,  471, 17, 'plPlugMapM-3782-55242-01.par'),
		(55243,  784,  471, 17, 'plPlugMapM-3782-55242-01.par'),
		(55243,  785,  786, 16, 'plPlugMapM-3774-55241-01.par'),
		(55243,  926,  786, 16, 'plPlugMapM-3774-55241-01.par'),
		(55243,  927,  928, 11, 'plPlugMapM-3852-55242-01.par'),
		(55243, 1193,  928, 11, 'plPlugMapM-3852-55242-01.par'),
		]

	alldx = []
	alldy = []

	figure(figsize=(6,6))
	for (mjd, gimgnum, compnum, cart, plugmapbasefn) in testInputs:
		fn = '../testfiles/%i/gimg-%04i.fits' % (mjd, gimgnum)
		plugmapfn = '../testfiles/%i/' % mjd + plugmapbasefn

		plate = int(re.match(r'plPlugMapM-(\d*)-', plugmapbasefn).group(1))

		comparefn = '../testfiles/%i/proc-gimg-%04i.fits' % (mjd, compnum)

		print
		print 'MJD %i  --  Gimg %04i  --  cart %i  --  plugmap %s  --  plate %i' % (mjd, gimgnum, cart, plugmapbasefn, plate)
		print

		gprobes = getGprobes(fiberinfofn, plugmapfn, cart)
		for k,v in gprobes.items():
			d = ducky()
			d.info = v
			d.enabled = True
			d.flags = 0
			gprobes[k] = d
	
		(flat, mask, fibers) = GI.analyzeFlat(fn, cart, gprobes, stamps=True)
		fibers = [f for f in fibers if not f.is_fake()]

		print 'Got %i fibers' % len(fibers)
		for f in fibers:
			print '  ', f

		outbase = '%i-%04i' % (mjd, gimgnum)

		compare = False
		if comparefn and os.path.exists(comparefn):
			compare = True
			p = pyfits.open(comparefn)[6].data
			xc = p.field('xCenter')
			yc = p.field('yCenter')
			for f in fibers:
				f.xs = xc[f.fiberid - 1]
				f.ys = yc[f.fiberid - 1]

			alldx += [f.xs - f.xcen for f in fibers]
			alldy += [f.ys - f.ycen for f in fibers]

		clf()
		plot_fibers(flat, fibers, centerxy=True, showaxes=True,
					starxy=compare)
		subplots_adjust(left=0.05, right=0.99, bottom=0.03, top=0.95,
						wspace=0.25, hspace=0.25)

		text(0.5, 0.98,
			 'MJD %i  -  Gimg %04i  -  Plate %i' % (mjd, gimgnum, plate),
			 transform=gcf().transFigure, fontsize=12,
			 horizontalalignment='center', verticalalignment='top')

		savefig(outbase + '.png')

		#clf()
		#plot_fiber_stamps(fibers)
		#savefig('55243-0001-stamps.png')

		#clf()
		#subplot(111)
		#subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.95,
		#				wspace=0.05, hspace=0.05)
		#imshow(flat, origin='lower', interpolation='nearest')
		#gray()
		#savefig('55243-0001-flat.png')
	
	clf()
	subplot(2,1,1)
	title('(Dustin - As-Run) fiber centroids')
	hist(array(alldx).ravel(), 20)
	xlabel('dx (pixels)')
	subplot(2,1,2)
	hist(array(alldy).ravel(), 20)
	xlabel('dy (pixels)')
	subplots_adjust(left=0.1, right=0.95, bottom=0.1, top=0.9,
					wspace=0.2, hspace=0.2)
	savefig('dxdy-hist.png')

	clf()
	subplot(111)
	title('(Dustin - As-Run) fiber centroids')
	plot(array(alldx).ravel(), array(alldy).ravel(), 'b.')
	xlabel('dx (pixels)')
	ylabel('dy (pixels)')
	subplots_adjust(left=0.2, right=0.95, bottom=0.1, top=0.9,
					wspace=0.2, hspace=0.2)
	savefig('dxdy.png')
