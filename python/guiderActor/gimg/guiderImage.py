import os.path
import numpy
from numpy import *
import ctypes
import pyfits
from scipy.ndimage.morphology import binary_closing, binary_dilation, binary_fill_holes, binary_erosion
from scipy.ndimage.measurements import label, center_of_mass, find_objects

import actorcore.utility.fits as actorFits

# A guider fiber and the star image seen through it.
class fiber(object):
	def __init__(self, fibid, xc=numpy.nan, yc=numpy.nan, r=numpy.nan, illr=numpy.nan):
		self.fiberid = fibid
		self.xcen = xc
		self.ycen = yc
		self.radius = r
		self.illrad = illr

		self.xs = numpy.nan
		self.ys = numpy.nan
		self.xyserr = numpy.nan
		self.fwhm = numpy.nan
		self.sky = numpy.nan
		self.mag = numpy.nan

		# self.rms ?  Used by masterThread.py

		self.fwhmErr = numpy.nan
		self.dx = numpy.nan
		self.dy = numpy.nan
		self.dRA = numpy.nan
		self.dDec = numpy.nan

		self.gprobe = None

	def __str__(self):
		return ('Fiber id %i: center %g,%g; star %g,%g; radius %g' %
				(self.fiberid, self.xcen, self.ycen, self.xs, self.ys, self.radius))

	def set_fake(self):
		self.xcen = numpy.nan

	def is_fake(self):
		return not isfinite(self.xcen)


# The following are ctypes classes for interaction with the ipGguide.c code.
class REGION(ctypes.Structure):
	_fields_ = [("nrow", ctypes.c_int),
				("ncol", ctypes.c_int),
				("rows_s16", ctypes.POINTER(ctypes.POINTER(ctypes.c_int16)))]

class MASK(ctypes.Structure):
	_fields_ = [("nrow", ctypes.c_int),
				("ncol", ctypes.c_int),
				("rows", ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)))]

class FIBERDATA(ctypes.Structure):
	_fields_ = [("g_nfibers", ctypes.c_int),
				("g_fid", ctypes.POINTER(ctypes.c_int32)),
				("g_xcen", ctypes.POINTER(ctypes.c_double)),
				("g_ycen", ctypes.POINTER(ctypes.c_double)),
				("g_fibrad", ctypes.POINTER(ctypes.c_double)),
				("g_illrad", ctypes.POINTER(ctypes.c_double)),
				("g_xs", ctypes.POINTER(ctypes.c_double)),
				("g_ys", ctypes.POINTER(ctypes.c_double)),
				("g_mag", ctypes.POINTER(ctypes.c_double)),
				("g_fwhm", ctypes.POINTER(ctypes.c_double)),
				("g_poserr", ctypes.POINTER(ctypes.c_double)),
				("g_fitbkgrd", ctypes.POINTER(ctypes.c_double)),
				("g_readnoise", ctypes.c_double),
				("g_npixmask", ctypes.c_int)]

def numpy_array_to_REGION(A):
	H, W = A.shape
	ptrtype = ctypes.POINTER(ctypes.c_int16)
	rows = (ptrtype*H)(*[row.ctypes.data_as(ptrtype) for row in A])
	return REGION(H, W, rows) 

def numpy_array_to_MASK(A):
	H, W = A.shape
	ptrtype = ctypes.POINTER(ctypes.c_uint8)
	rows = (ptrtype*H)(*[row.ctypes.data_as(ptrtype) for row in A])
	return MASK(H, W, rows) 

class GuiderImageAnalysis(object):
	'''
	A class for analyzing the images taken by the guiding camera.

	gimg_filename = 'gimg-0400.fits'
	GI = GuiderImageAnalysis(gimg_filename, cmd)
	# cmd must have methods "inform(string)", "warn(string)".
	fibers = GI.findFibers(gState.gprobes)

	# run guider control loop...

	GI.writeFITS(actorState.models, guideCmd, frameInfo, gState.gprobes)

	'''
	def __init__(self, gimgfn, cmd=None):
		self.gimgfn = gimgfn
		# set during findFibers():
		self.fibers = None
		self.guiderImage = None
		self.guiderHeader = None
		self.maskImage = None

		if cmd:
			self.informFunc = cmd.inform
			self.warnFunc = cmd.warn
		else:
			self.informFunc = None
			self.warnFunc = None

		# "Big" (acquisition) fibers are bigger than this pixel
		# radius.  The older SDSS cartridges don't declare (in the
		# gcamFiberInfo.par file) the larger fibers to be ACQUIRE,
		# though they are declared to have radii of 14.1 pixels (vs
		# 8.5 for the GUIDE fibers).  We therefore cut on this radius.
		#
		self.bigFiberRadius = 12.

		# Saturation level.
		self.saturationLevel = 0x8000
		# The value to replace saturated pixels by.
		self.saturationReplacement = 0x7fff

		# The factor by which guider images are binned down.
		# That is, unbinned (flat) images are this factor bigger in
		# each dimension.
		self.binning = 2

	# For ease of testing...
	def warn(self, s):
		if self.warnFunc is None:
			print 'warning:', s
		else:
			self.warnFunc('text="' + s + '"')
	def inform(self, s):
		if self.informFunc is None:
			print 'info:', s
		else:
			self.informFunc('text="' + s + '"')

	def debug(self, s):
		#print s
		pass

	def findDarkAndFlat(self, gimgfn, fitsheader):
		''' findDarkAndFlat(...)

		Returns the filenames containing the dark and flat images for
		the given guider-camera image.

		These are listed in the gimg-####.fits header; this method exists
		to make testing easier, and to make path name magic more explicit.

		DARKFILE= '/data/gcam/55205/gimg-0003.fits'
		FLATFILE= '/data/gcam/55205/gimg-0224.fits'
		'''
		return (fitsheader['DARKFILE'], fitsheader['FLATFILE'])

	def getProcessedOutputName(self, imgfn):
		(dirname, filename) = os.path.split(imgfn)
		outname = 'proc-%s' % (filename)
		procpath = os.path.join(dirname, outname)
		return procpath

	def addPixelWcs(self, header, wcsName=""):
		"""Add a WCS that sets the bottom left pixel's centre to be (0.5, 0.5)"""
		header.update("CRVAL1%s" % wcsName, 0, "(output) Column pixel of Reference Pixel")
		header.update("CRVAL2%s" % wcsName, 0, "(output) Row pixel of Reference Pixel")
		header.update("CRPIX1%s" % wcsName, 0.5, "Column Pixel Coordinate of Reference")
		header.update("CRPIX2%s" % wcsName, 0.5, "Row Pixel Coordinate of Reference")
		header.update("CTYPE1%s" % wcsName, "LINEAR", "Type of projection")
		header.update("CTYPE1%s" % wcsName, "LINEAR", "Type of projection")
		header.update("CUNIT1%s" % wcsName, "PIXEL", "Column unit")
		header.update("CUNIT2%s" % wcsName, "PIXEL", "Row unit")

	def fillPrimaryHDU(self, cmd, models, imageHDU, frameInfo, objectname):
		""" Add in all the site and environment keywords. """
		try:
			imageHDU.header.update('OBJECT', objectname, '')
			imageHDU.header.update('GCAMSCAL', frameInfo.guideCameraScale, 'guide camera plate scale (mm/pixel)')
			imageHDU.header.update('PLATSCAL', frameInfo.plugPlateScale, 'plug plate scale (mm/degree)')
			tccCards = actorFits.tccCards(models, cmd=cmd)
			actorFits.extendHeader(cmd, imageHDU.header, tccCards)
			mcpCards = actorFits.mcpCards(models, cmd=cmd)
			actorFits.extendHeader(cmd, imageHDU.header, mcpCards)
			plateCards = actorFits.plateCards(models, cmd=cmd)
			actorFits.extendHeader(cmd, imageHDU.header, plateCards)
			guiderCards = self.getGuideloopCards(cmd, frameInfo)
			actorFits.extendHeader(cmd, imageHDU.header, guiderCards)
			self.addPixelWcs(imageHDU.header)
		except Exception, e:
			self.warn('!!!!! failed to fill out primary HDU  !!!!! (%s)' % (e))

	def getGuideloopCards(self, cmd, frameInfo):
		defs = (('dRA', 'DRA', 'measured offset in RA, deg'),
				('dDec', 'DDec', 'measured offset in Dec, deg'),
				('dRot', 'DRot', 'measured rotator offset, deg'),
				('dFocus', 'DFocus', 'measured focus offset, um '),
				('dScale', 'DScale', 'measured scale offset, %'),
				('filtRA', 'FILTRA', 'filtered offset in RA, deg'),
				('filtDec', 'FILTDec', 'filtered offset in Dec, deg'),
				('filtRot', 'FILTRot', 'filtered rotator offset, deg'),
				('filtFocus', 'FILTFcus', 'filtered focus offset, um '),
				('filtScale', 'FILTScle', 'filtered scale offset, %'),
				('offsetRA', 'OFFRA', 'applied offset in RA, deg'),
				('offsetDec', 'OFFDec', 'applied offset in Dec, deg'),
				('offsetRot', 'OFFRot', 'applied rotator offset, deg'),
				('offsetFocus', 'OFFFocus', 'applied focus offset, um'),
				('offsetScale', 'OFFScale', 'applied scale offset, %'))
		cards = []
		for name, fitsName, comment in defs:
			try:
				val = getattr(frameInfo,name)
				if val != val:
					val = -99999.9 # F.ing F.TS
				c = actorFits.makeCard(cmd, fitsName, val, comment)
				cards.append(c)
			except Exception, e:
				self.warn('failed to make guider card %s=%s (%s)' % (name, val, e))
		return cards

	def getStampHDUs(self, fibers, bg, image, mask):
		r = int(ceil(max([f.radius for f in fibers])))
		stamps = []
		maskstamps = []
		for f in fibers:
			xc = int(f.xcen + 0.5)
			yc = int(f.ycen + 0.5)
			rot = -f.gprobe.info.rotStar2Sky
			self.debug("rotating fiber %d at (%d,%d) by %0.1f degrees" % (f.fiberid, xc, yc, rot))
			# Rotate the fiber image...
			stamp = image[yc-r:yc+r+1, xc-r:xc+r+1].astype(int16)
			rstamp = zeros_like(stamp)
			self.libguide.rotate_region(numpy_array_to_REGION(stamp),
										numpy_array_to_REGION(rstamp),
										rot)
			stamps.append(rstamp)
			# Rotate the mask image...
			stamp = mask[yc-r:yc+r+1, xc-r:xc+r+1].astype(uint8)
			rstamp = zeros_like(stamp)
			self.libguide.rotate_mask(numpy_array_to_MASK(stamp),
									  numpy_array_to_MASK(rstamp),
									  rot)
			maskstamps.append(rstamp)

		# Stack the stamps into one image.
		stamps = vstack(stamps)
		maskstamps = vstack(maskstamps)
		# Replace zeroes by bg
		stamps[stamps==0] = bg
		return [pyfits.ImageHDU(stamps), pyfits.ImageHDU(maskstamps)]

	def _getProcGimgHDUList(self, primhdr, gprobes, fibers, image, mask):
		imageBackground = median(image)
		imageHDU = pyfits.PrimaryHDU(image, header=primhdr)
		imageHDU.header.update('SDSSFMT', 'GPROC 1 2', 'type major minor version for this file')
		imageHDU.header.update('IMGBACK', imageBackground, 'crude background for entire image. For displays.')

		try:
			# List the fibers by fiber id.
			fiberids = gprobes.keys()
			fiberids.sort()
			sfibers = []
			myfibs = dict([(f.fiberid,f) for f in fibers])
			for fid in fiberids:
				if fid in myfibs:
					sfibers.append(myfibs[fid])
				else:
					# Put in NaN fake fibers for ones that weren't found.
					fake = fiber(fid)
					fake.gprobe = gprobes[fid]
					sfibers.append(fake)
			fibers = sfibers

			# Split into small and big fibers.
			# Also create the columns "stampInds" and "stampSizes"
			# for the output table.
			smalls = []
			bigs = []
			stampInds = []
			stampSizes = []
			for f in fibers:
				if f.is_fake():
					stampSizes.append(0)
					stampInds.append(-1)
				elif f.radius < self.bigFiberRadius:
					# must do this before appending to smalls!
					stampInds.append(len(smalls))
					stampSizes.append(1)
					smalls.append(f)
				else:
					stampInds.append(len(bigs))
					stampSizes.append(2)
					bigs.append(f)

			hdulist = pyfits.HDUList()
			hdulist.append(imageHDU)
			hdulist.append(pyfits.ImageHDU(mask))
			hdulist += self.getStampHDUs(smalls, imageBackground, image, mask)
			hdulist += self.getStampHDUs(bigs, imageBackground, image, mask)

			pixunit = 'guidercam pixels (binned)'
			gpfields = [
				# FITScol,      FITStype, unit
				('enabled',        'L',   None),
				('flags',          'L',   None),
						]
			gpinfofields = [
				# FITScol,      FITStype, unit
				('exists',         'L',   None),
				('xFocal',         'E',   'plate mm'),
				('yFocal',         'E',   'plate mm'),
				('radius',         'E',   pixunit),
				('xFerruleOffset', 'E',   None),
				('yFerruleOffset', 'E',   None),
				('rotation',       'E',   None),
				('rotStar2Sky',    'E',   None),
				('focusOffset',    'E',   'micrometers'),
				('fiber_type',     'A20', None),
				]
			ffields = [
				# FITScol,  variable, FITStype, unit
				('fiberid', None,     'I', None),
				('xCenter', 'xcen',   'E', pixunit),
				('yCenter', 'ycen',   'E', pixunit),
				('xstar',   'xs',     'E', pixunit),
				('ystar',   'ys',     'E', pixunit),
				('dx',      None,     'E', 'residual in mm, guidercam frame'),
				('dy',      None,     'E', 'residual in mm, guidercam frame'),
				('dRA',     None,     'E', 'residual in mm, plate frame'),
				('dDec',    None,     'E', 'residual in mm, plate frame'),
				('fwhm',    None,     'E', 'arcsec'),
				('poserr',  'xyserr', 'E', None),
				]
			
			cols = []
			for name,fitstype,units in gpfields:
				cols.append(pyfits.Column(name=name, format=fitstype, unit=units,
										  array=numpy.array([getattr(f.gprobe, name) for f in fibers])))
			for name,fitstype,units in gpinfofields:
				cols.append(pyfits.Column(name=name, format=fitstype, unit=units,
										  array=numpy.array([getattr(f.gprobe.info, name) for f in fibers])))
			for name,atname,fitstype,units in ffields:
				cols.append(pyfits.Column(name=name, format=fitstype, unit=units,
										  array=numpy.array([getattr(f, atname or name) for f in fibers])))

			cols.append(pyfits.Column(name='stampSize', format='I', array=numpy.array(stampSizes)))
			cols.append(pyfits.Column(name='stampIdx', format='I', array=numpy.array(stampInds)))

			hdulist.append(pyfits.new_table(cols))
		except Exception, e:
			self.warn("text='could not write proc- guider file: %s'" % (e,))
			return None
		return hdulist
		

	def writeFITS(self, models, cmd, frameInfo, gprobes):
		if not self.fibers:
			raise Exception('must call findFibers() before writeFITS()')
		fibers = self.fibers
		gimg = self.guiderImage
		hdr = self.guiderHeader

		procpath = self.getProcessedOutputName(self.gimgfn)
		objectname = os.path.splitext(self.gimgfn)[0]

		hdulist = self._getProcGimgHDUList(hdr, gprobes, fibers, gimg, self.maskImage)
		imageHDU = hdulist[0]
		imageHDU.header.update('SEEING', frameInfo.seeing if frameInfo.seeing is not numpy.nan else 0.0,
							   'Estimate of current seeing, arcsec fwhm')
		self.fillPrimaryHDU(cmd, models, imageHDU, frameInfo, objectname)
		hdulist.writeto(procpath, clobber=True)
		self.inform('file=%s' % procpath)

	def findFibers(self, gprobes):
		''' findFibers(gprobes)

		* gprobes is from masterThread.py -- it must be a dict from
		  fiber id (int) to Gprobe objects.  The "enabled" and "info"
		  fields are used; "info" must have "radius", "xCenter", "yCenter",
		  and "rotStar2Sky" fields.

		Analyze a single image from the guider camera, finding fiber
		centers and star centers.

		The fiber centers are found by referring to the associated guider
		flat.  Since this flat is shared by many guider-cam images, the
		results of analyzing it are cached in a "proc-gimg-" file for the flat.

		Returns a list of fibers; also sets several fields in this object.

		The list of fibers contains an entry for each fiber found.
		'''
		assert(self.gimgfn)

		# Load C library "ipGguide.c"
		path = os.path.expandvars("$GUIDERACTOR_DIR/lib/libguide.so")
		libguide = ctypes.CDLL(path)
		if not libguide:
			self.warn('Failed to load "libguide.so" from %s ($GUIDERACTOR_DIR/lib/libguide.so)' % path)
		libguide.gfindstars.argtypes = [ctypes.POINTER(REGION), ctypes.POINTER(FIBERDATA), ctypes.c_int]
		libguide.gfindstars.restype = ctypes.c_int
		libguide.fiberdata_new.argtypes = [ctypes.c_int]
		libguide.fiberdata_new.restype = ctypes.POINTER(FIBERDATA)
		libguide.fiberdata_free.argtypes = [ctypes.POINTER(FIBERDATA)]
		libguide.fiberdata_free.restype = None
		libguide.rotate_region.argtypes = [ctypes.POINTER(REGION), ctypes.POINTER(REGION), ctypes.c_float]
		libguide.rotate_region.restype = None
		libguide.rotate_mask.argtypes = [ctypes.POINTER(MASK), ctypes.POINTER(MASK), ctypes.c_float]
		libguide.rotate_mask.restype = None
		self.libguide = libguide

		# Load guider-cam image.
		self.debug('Reading guider-cam image %s' % self.gimgfn)
		p = pyfits.open(self.gimgfn)
		image = p[0].data
		hdr = p[0].header

		# We can't cope with bright pixels. Hack a fix.
		sat = (image >= self.saturationLevel)
		if any(sat):
			self.warn('the exposure has %i saturated pixels' % sum(sat))
		image[sat] = self.saturationReplacement

		# Get dark and flat
		(darkfn, flatfn) = self.findDarkAndFlat(self.gimgfn, hdr)
		cartridgeId = int(hdr['FLATCART'])

		# FIXME -- we currently don't do anything with the dark frame.
		#   we'll need hdr['EXPTIME'] if we do.
		# FIXME -- filter probes here for !exists, !tritium ?

		self.debug('Using flat image %s' % flatfn)
		(flat, mask, fibers) = self.flat_analyze(flatfn, cartridgeId, gprobes)

		# FIXME -- presumably we want to mask pixels that were saturated?
		

		# FIXME -- we currently don't apply the flat.
		if False:
			# Subtract background.
			image -= median(image.ravel())
			# Divide by the flat (avoiding NaN where the flat is zero)
			image /= (flat + (flat == 0)*1)
			self.debug('After flattening: image range: %g to %g' % (image.min(), image.max()))

		# Zero out parts of the image that are masked out.
		# In this mask convention, 0 = good, 1 = bad.
		image[mask] = 0

		doplots = False
		if doplots:
			plot_fibers(flat, fibers, axes=True, centerxy=True)
			savefig('flat.png')
			figure(figsize=(6,6))
			plot_fibers(image, fibers, axes=True, centerxy=True)
			savefig('flattened.png')

		self.guiderImage = image
		self.guiderHeader = hdr
		self.maskImage = mask

		goodfibers = [f for f in fibers if not f.is_fake()]
		#print '%i fibers; %i good.' % (len(fibers), len(goodfibers))

		# Convert data types for "gfindstars"...
		# This object must live until after gfindstars() !
		img16 = image.astype(int16)
		self.debug('Image (i16) range: %i to %i' % (img16.min(), img16.max()))
		c_image = numpy_array_to_REGION(img16)
		c_fibers = libguide.fiberdata_new(len(goodfibers))

		for i,f in enumerate(goodfibers):
			c_fibers[0].g_fid[i] = f.fiberid
			c_fibers[0].g_xcen[i] = f.xcen
			c_fibers[0].g_ycen[i] = f.ycen
			c_fibers[0].g_fibrad[i] = f.radius
			# FIXME ??
			c_fibers[0].g_illrad[i] = f.radius

		# mode=1: data frame; 0=spot frame
		mode = 1
		res = libguide.gfindstars(ctypes.byref(c_image), c_fibers, mode)
		# SH_SUCCESS is this following nutty number...
		if res == int(numpy.uint32(0x8001c009)):
			self.debug('gfindstars returned successfully.')
		else:
			self.warn('gfindstars() returned an error code: %i' % res)

		# pull star positions out of c_fibers, stuff outputs...
		for i,f in enumerate(goodfibers):
			f.xs     = c_fibers[0].g_xs[i]
			f.ys     = c_fibers[0].g_ys[i]
			f.xyserr = c_fibers[0].g_poserr[i]
			f.fwhm   = c_fibers[0].g_fwhm[i]
			f.sky    = c_fibers[0].g_fitbkgrd[i]
			f.mag    = c_fibers[0].g_mag[i]

		libguide.fiberdata_free(c_fibers)

		if doplots:
			plot_fibers(image, fibers, axes=True, centerxy=True, starxy=True, R=11)
			print 'Writing stars.png'
			savefig('stars.png')

		self.fibers = fibers
		return fibers

	@staticmethod
	def readProcessedFlat(flatfn, gprobes):
		p = pyfits.open(flatfn)
		flat = p[0].data
		mask = p[1].data
		# small fiber stamps & masks
		# big fiber stamps & masks
		table = p[6].data
		x = table.field('xcenter')
		y = table.field('ycenter')
		radius = table.field('radius')
		fiberid = table.field('fiberid')
		fibers = []
		for xi,yi,ri,fi in zip(x,y,radius,fiberid):
			f = fiber(fi, xi, yi, ri, 0)
			f.gprobe = gprobes.get(fi)
			fibers.append(f)
		return (flat, mask, fibers)

	# Returns (mask, flat, fibers)
	def flat_analyze(self, flatfn, cartridgeId, gprobes):
		flatout = self.getProcessedOutputName(flatfn)

		if os.path.exists(flatout):
			self.inform('Reading processed flat-field from %s' % flatout)
			try:
				return readProcessedFlat(flatout, gprobes)
			except:
				self.warn('Failed to read processed flat-field from %s; regenerating it.' % flatout)

		img = pyfits.getdata(flatfn)

		# FIXME -- we KNOW the area (ie, the number of pixels) of the
		# fibers -- we could choose the threshold appropriately.

		# HACK -- find threshold level inefficiently.
		# This is the threshold level that was used in "gfindfibers".
		i2 = img.copy().ravel()
		I = argsort(i2)
		# median
		med = i2[I[len(I)/2]]
		# pk == 99th percentile
		pk = i2[I[int(len(I)*0.99)]]
		thresh = (med + pk)/2.

		# Threshold image
		T = (img > thresh)
		# Fix nicks in fibers, and fill holes (necessary for the acquisition fibers)
		T = binary_closing(T, iterations=10)

		# Find the background in regions below the threshold.
		background = median(img[logical_not(T)].ravel())
		self.debug('Background in flat %s: %g' % (flatfn, background))
	
		# Make the mask a bit smaller than the thresholded fibers.
		mask = binary_erosion(T, iterations=3)

		# Label connected components.
		(L,nl) = label(T)

		# FIXME -- the following could be made a bit quicker by using:
		#    objs = find_objects(L, nl)
		# ==> "objs" is a list of (slice-rows, slice-cols)

		BIN = self.binning

		fibers = []
		for i in range(1, nl+1):
			# find pixels labelled as belonging to object i.
			obji = (L == i)
			# ri,ci = nonzero(obji)
			# print 'fiber', i, 'extent', ci.min(), ci.max(), ri.min(), ri.max()
			npix = sum(obji)
			cm = center_of_mass(obji)
			# center_of_mass returns row,column... swap to x,y
			xc = cm[1]
			yc = cm[0]
			# x,y,radius / BIN because the flat is unbinned pixels, but we want
			# to report in binned pixels.
			# FIXME -- pixel coordinate conventions here?
			fibers.append(fiber(-1, xc/BIN, yc/BIN, sqrt(npix/pi)/BIN, -1))

		# Match up the fibers with the known probes.

		# Filter fibers that are not within X% of the size of a probe.
		# This should drop small objects (eg, cosmic rays)
		proberads = unique([p.info.radius for p in gprobes.values()])
		keepfibers = []
		for f in fibers:
			dr = abs((f.radius - proberads)/proberads).min()
			# Typically < 7%
			if dr < 0.25:
				keepfibers.append(f)
			else:
				self.inform('Rejecting fiber at (%i,%i) in unbinned pixel coords, with radius %g: too far from expected radii %s' %
						  (f.xcen, f.ycen, f.radius, '{' + ', '.join(['%g'%r for r in proberads]) + '}'))
		fibers = keepfibers

		# Find a single x,y offset by testing possibly corresponding
		# pairs of fibers/probes and checking how many fibers are
		# where you expect them to be.
		maxhits = 0
		best = None
		FX,FY = array([f.xcen for f in fibers]), array([f.ycen for f in fibers])
		PX = array([p.info.xCenter for p in gprobes.values()])
		PY = array([p.info.yCenter for p in gprobes.values()])
		(H,W) = img.shape
		for i,f in enumerate(fibers):
			for j,(px,py) in enumerate(zip(PX,PY)):
				dx,dy = f.xcen - px, f.ycen - py
				# If this (dx,dy) would put some of the expected probes outside the image, skip it.
				if (min(PX + dx) < 0 or min(PY + dy) < 0 or
					max(PX + dx) > W/BIN or max(PY + dy) > H/BIN):
					continue
				# Look for matches...
				fmatch = []
				for k,pp in gprobes.items():
					# Find the distance from this probe to each fiber...
					D = sqrt(((pp.info.yCenter + dy) - FY)**2 + ((pp.info.xCenter + dx) - FX)**2)
					a = argmin(D)
					# If the nearest one is within range...
					if D[a] < fibers[a].radius:
						# Fiber "a" is probe id "k".
						# Compute the dx,dy implied by this match...
						mydx = FX[a] - (pp.info.xCenter + dx)
						mydy = FY[a] - (pp.info.yCenter + dy)
						fmatch.append((a,k, mydx, mydy))

				nhits = len(fmatch)
				if nhits > maxhits:
					# FIXME -- check for conflicts in 'fmatch' here?
					maxhits = nhits
					best = fmatch
				if nhits == len(gprobes):
					break

		if best is None:
			# How can this happen?  No fibers or no probes...
			self.warn("This can't happen?  No match fibers/probes")
			return None

		fmatch = best
		# Check for duplicates...
		fmap = {}
		for fi,probei,dx,dy in fmatch:
			if fi in fmap:
				self.warn('Fiber %i wants to be match to probe %i and %i.' % (fi, fmap[fi], probei))
				continue
			if probei in fmap.values():
				self.warn('Fiber %i wants to be match to already-matched probe %i.' % (fi, probei))
				continue
			fmap[fi] = probei
		dx = mean([dx for fi,probei,dx,dy in fmatch])
		dy = mean([dy for fi,probei,dx,dy in fmatch])
		self.inform('Matched %i fibers, with dx,dy = (%g,%g)' % (len(fmap), dx, dy))

		# Filter out those with no match...
		fibers = [f for i,f in enumerate(fibers) if i in fmap]

		# Record the fiber id, and remember the gprobe...
		for i,f in enumerate(fibers):
			f.fiberid = fmap[i]
			f.gprobe = gprobes[f.fiberid]

		# Reorder fibers by fiberid.
		I = argsort(array([f.fiberid for f in fibers]))
		fibers = [fibers[i] for i in I]
		for f in fibers:
			self.debug('Fiber id %i at (%.1f, %.1f)' % (f.fiberid, f.xcen-dx, f.ycen-dy))

		# Create the flat image.
		flat = zeros_like(img).astype(float)
		for i in range(1, nl+1):
			# find pixels belonging to object i.
			obji = (L == i)
			# FIXME -- flat -- normalize by max? median? sum? of this fiber
			# FIXME -- clipping, etc.
			flat[obji] += clip((img[obji]-background) / median(img[obji]-background), 0.5, 1.5)
			# objflat = (img[obji]-background) / median(img[obji]-background)
			# print 'objflat range:', objflat.min(), objflat.max()

		# Bin down the mask and flat.
		bmask = zeros((mask.shape[0]/BIN, mask.shape[1]/BIN), bool)
		for i in range(BIN):
			for j in range(BIN):
				bmask = logical_or(bmask, mask[i::BIN,j::BIN])
		# The "gfindstars" function wants the mask to be 0=good.
		bmask = logical_not(bmask)
		mask = bmask
		mask = mask.astype(uint8)

		bflat = zeros((flat.shape[0]/BIN, flat.shape[1]/BIN), float)
		for i in range(BIN):
			for j in range(BIN):
				bflat += flat[i::BIN,j::BIN]
		bflat /= (BIN*BIN)
		flat = bflat

		# Write output file... copy header cards from input image.
		# DX?  DY?  Any other stats in here?
		hdr = pyfits.getheader(flatfn)
		pixunit = 'binned guider-camera pixels'

		# For writing fiber postage stamps, fill in rotation fields.
		for f in fibers:
			if f.is_fake():
				continue
			f.gprobe.info.rotStar2Sky = 90 + f.gprobe.info.rotation - f.gprobe.info.phi

		hdulist = self._getProcGimgHDUList(hdr, gprobes, fibers, flat, mask)
		if hdulist is None:
			self.warn('Failed to create processed flat file')
			return (flat, mask, fibers)

		hdulist.writeto(flatout, clobber=True)
		# Now read that file we just wrote...
		return readProcessedFlat(flatout, gprobes)

