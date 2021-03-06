#!/usr/bin/env python
#
# Given CUE file, uses FFMPEG to extract tracks from AV file (eg. mp3,
# wav, flac, etc.). Input AV must be ffmpeg compatible format.
#
# INPUT
# ----------------
# Use '--help' to get descrption on input parameters.
#
# "path.cfg" - File in the same directory this .py file is in, if exists,
#              first line path is added to the PATH environment variable.
#              If first line is a path to existing file, it is assumed to be Ffmpeg
#              executable itself, and is used.
#
#
import os, sys, optparse, time, datetime
import re   ## Regex
import subprocess


## Returns tuple of 2 elements, seconds as double and millisecs as int.
## Matches various HMS strings, ranging from "1:04:54.010" to "3:24".
def spi_ConvHMSToInteger( inp ):   ## [uOHgcik] ##{
	mt2 = re.search("^ \\s* (\\d+)(:\\d+)(?:([:\\.]\\d+)(?:(\\.\\d+)|)|)", inp, re.I|re.X )
	if not mt2:
		return (0,0,)
	mt2 = [ mt2.group(1), mt2.group(2), mt2.group(3), mt2.group(4), ]
	mt2 = filter( (lambda a: a != None), mt2 )
	if( mt2[-1][0] == "." ):
		## For fractional part, if needed, add trailing zeros. Eg. convert ".33" to ".330".
		szVal = str( re.search("(\\d{1,3})", mt2[-1] ).group(1) )
		mt2[-1] = (".%s%s" % (szVal, ("0" * max( (3-len(szVal)), 0 )),))
	if( mt2[-1][0] != "." ):
		mt2.append(".000")
	for k in range( 0, max( 4 - len(mt2), 0 ) ):
		mt2.insert(0,"0")   ## push_front("0")
	mt2 = map( (lambda a: int(re.search("(\\d+)",a).group(1))), mt2 )
	mt2[3] = min( mt2[3], 999 )
	tmd2 = datetime.timedelta( hours = mt2[0], minutes = mt2[1],
				seconds = mt2[2], milliseconds = mt2[3] )
	nSecs = tmd2.total_seconds()
	nMilliSecs = int( nSecs * 1000 )
	return ( nSecs, nMilliSecs,)
##   [uOHgcik] ##}

## Converts value in seconds (float or int) to "H:MM:SS.zzz" string.
## eg. 203.28 --> "0:03:23.280"
def spi_SecsToHmsStr( secs ):
	secs = float(secs)
	secs2 = int(secs)
	z = int( ( float(("0.%s" % (str(secs).split(".",1)[1],))) * 1000.0 ) )
	##z = int( ( (secs - secs2) * 1000.0 ) )
	m, s = divmod( secs2, 60 )
	h, m = divmod( m, 60 )
	return ("%d:%02d:%02d.%03d" % (h,m,s,z,))

def spi_SecsToMinutesColonSecsStr( secs ):
	secs = float(secs)
	secs2 = int(secs)
	##z = int( ( float(("0.%s" % (str(secs).split(".",1)[1],))) * 1000.0 ) )
	m, s = divmod( secs2, 60 )
	h, m = divmod( m, 60 )
	m += h * 60
	return ("%d:%02d:00" % (m,s,))

## Gets media length in milliseconds for given AV file
## via Ffmpeg executable.
## Returns tupple of 3 elements:
## <succsess, error-message, lenth-in-millis>
def spi_GetMediaLengthViaFfmpeg( szFfm, szImf ):   ## [HzoadbL79] ##{
	g1z  = type("", (), {"group": (lambda self,g: ""),} )()
	cmd2 = ("\x22%s\x22 -hide_banner -i \x22%s\x22" % (szFfm, szImf,) )
	rs2  = 0; szStd = ""
	try:
		szStd = subprocess.check_output( cmd2, shell=1, stderr=subprocess.STDOUT )
	except subprocess.CalledProcessError as e:
		rs2 = e.returncode
		szStd = e.output
	if( rs2 not in [0,1,] ):
		msg2 = ("Ffmpeg failed (code:%d)." % (rs2,))
		return (0,msg2,0,)
	nLenMillis = 0
	ar2 = szStd.splitlines()
	for a in ar2:   ## [pvcF43nUaW] ##{
		szRe = " ^\\s*( (?: Stream\\s*\\# ) | (?: Duration\\:\\s+ ) )"
		sz3 = ( ( re.search( szRe, a, re.I|re.X ) or g1z ).group(1) )
		if( len(sz3) ):
			if( not nLenMillis ):
				## Eg. "Duration: 00:54:49.29,"
				re2 = "Duration: .+? ([\\d+\\:\\.]+)"
				drn2 = ( ( re.search( re2, a, re.I|re.X ) or g1z ).group(1) )
				if( len(drn2) ):
					nLenMillis = spi_ConvHMSToInteger( drn2 )[1]
	## [pvcF43nUaW] ##}
	if( not nLenMillis ):
		return (0,"Length not found in the Ffmpeg output.",0,)
	return (1,"",nLenMillis,)
## [HzoadbL79] ##}

def spi_ParseCUETracks( szCue, szImf ):    #{    #[iS8JD0ef0E]
	g1z2 = re.search("()","");
	reQtdStr = re.compile("\\x22(.*?)\\x22")
	lines2 = open(szCue).read().splitlines()
	print("Num lines: %d" % (len(lines2),) )
	tracks4 = []; trk = {}; nTrcks = 0; nErr2 = 0
	for i in range(0, len(lines2) ):
		ln2 = lines2[i].strip()
		if( i==0 and ln2.find("\xEF\xBB\xBF") == 0 ):   ## UTF-8 BOM check.
			ln2 = ln2[3:]
		if( not len(szImf) and ln2.find("FILE") == 0 ):     ## eg. ''FILE "a.mp3" MP3''
			s = ( ( reQtdStr.search(ln2) or g1z2 ).group(1) )
			if( not len(s) ):    ## 0x22=dbl-quote, 0x27=single-quote.
				s = ( ( re.search("FILE\\s+([^\\s\\x22]+)", ln2) or g1z2 ).group(1) )
			szImf = ( s if s else szImf )
			if( not os.path.isabs(szImf) and len(szCue) ):
				print("INFO: prefixing AV file path from CUE with dir-name of the CUE file.")
				szImf = ("%s/%s" % (os.path.dirname(szCue), szImf,))
		elif( ln2.find("TRACK") == 0 ):
			if( len(trk) ):
				##trk["idx2"] = len(tracks4)
				##trk2 = trk.copy()
				trk2 = {"ath":"", "ttl":"", "idx2": len(tracks4),}
				trk2.update( trk )
				trk = trk2
				#raw_input("....")
				tracks4.append( trk.copy() )
			trk.clear()
			nTrcks += 1
		if nTrcks:
			if( ln2.find("TITLE") == 0 ):
				s = ( ( reQtdStr.search(ln2) or g1z2 ).group(1) )
				trk["ttl"] = s
			elif( (ln2.find("PERFORMER") == 0) or (ln2.find("AUTHOR") == 0) ):
				s = ( ( reQtdStr.search(ln2) or g1z2 ).group(1) )
				trk["ath"] = s
			elif( re.search("^INDEX \\s+ 01", ln2, re.I|re.X ) ):   ## eg. "INDEX 01 06:03:00"
				mt3 = re.search("(\\d+):(\\d+):(\\d+)", ln2, re.I|re.X )   ## format is: mins:secs:frames, 1s=75 frames
				if mt3:
					tm3 = [ mt3.group(1), mt3.group(2), mt3.group(3), ]
					tm3 = map( (lambda a: int(a)), tm3 )
					tmd = datetime.timedelta( minutes = tm3[0], seconds = ( float(tm3[1]) + float(tm3[2]) / 75.0) )
					trk["tm2"] = tmd.total_seconds()
				else:
					print("ERROR: bad time format of the 'INDEX' at line: %d." % (i,) )
					nErr2 += 1
	if( len(trk) ):
		trk2 = {"ath":"", "ttl":"", "idx2": len(tracks4),}
		trk2.update( trk )
		trk = trk2
		tracks4.append( trk.copy() )
		trk.clear()
	return (tracks4,szImf,nErr2,)
#}    #[iS8JD0ef0E]

def spi_ParseTxtHmsTracks( szInpFnm ):   #{
	g1z3 = re.search("()","");
	nErr3 = 0
	##reQtdStr2 = re.compile("\\x22(.*?)\\x22")
	lines2 = open(szInpFnm).read().splitlines()
	print("Num lines.c: %d" % (len(lines2),) )
	## 1:04:54.010 xxxxx - xxxxxx xxx
	tracks4 = []; trk = {}; nTrcks = 0; nErr2 = 0
	for i in range(0, len(lines2) ):
		ln3 = lines2[i].strip()
		##trk2 = {"tm2": 0, "ttl": "", "ath": "",}
		## re to match various HMS strings, ex. from "1:04:54.010" to "3:24".
		mt4 = re.search("(\\d+)(:\\d+)(?:([:\\.]\\d+)(?:(\\.\\d+)|)|)", ln3 )
		if mt4:
			trk2 = {"idx2":i,}
			mt2 = [ mt4.group(1), mt4.group(2), mt4.group(3), mt4.group(4), ]
			mt2 = filter( (lambda a: a != None), mt2 )
			if( mt2[-1][0] != "." ):
				mt2.append(".000")
			for k in range( 0, max( 4 - len(mt2), 0 ) ):
				mt2.insert(0,"0")   ## push_front("0")
			mt2 = map( (lambda a: int(re.search("\\d+",a).group(0)) ), mt2 )
			mt2[3] = min( mt2[3], 999 )
			##print("ln-%d: [%d,%02d,%02d,%03d]" % (i+1, mt2[0], mt2[1], mt2[2], mt2[3],))
			tmd2 = datetime.timedelta( hours = mt2[0], minutes = mt2[1],
						seconds = mt2[2], milliseconds = mt2[3] )
			trk2["tm2"] = tmd2.total_seconds()
			if 1:
				## extract ARTIST-TITLE from the line.
				ln4 = ln3
				if( ln3.find( mt4.group(0) ) == 0 ):
					ln4 = ln3[ len(mt4.group(0)) : ]
				pos = ln4.find("\x20-")
				if( 1+pos ):
					trk2["ttl"] = ln4[ pos :     ].strip("\x20-\r\n")
					trk2["ath"] = ln4[ 0   : pos ].strip("\x20-\r\n")
				else:
					trk2["ath"] = ""
					trk2["ttl"] = ln4.strip("\x20-\r\n")
			##print("ln-%d: %-20s - [%s]" % (i+1, ("[%s]" % (trk2["ttl"],)), trk2["ath"],))
			tracks4.append(trk2)
		else:
			nErr3 += 1
			print("WARN: Line %d, no track info." % (i+1,))
	return (tracks4,nErr3,)
#}

def spi_GenerateCueDataGivenLen( nTotalLenSecs, nSplitLenSecs ):  ##{
	nNumSplits = int(nTotalLenSecs / nSplitLenSecs)
	nNumSplits += (1 if divmod( nTotalLenSecs, nSplitLenSecs )[1] else 0)
	tabs2 = "\x20\x20\x20\x20"
	data2 = ""
	data2 += "PERFORMER \x22"+"VA\x22\n"
	data2 += "TITLE \x22"+"No Title\x22\n"
	data2 += ("FILE \x22%s\x22 WAV\n" % (os.path.basename(szImf),))
	for ii2 in range(0,nNumSplits):
		nPosSecs = ii2 * nSplitLenSecs
		szMntSecs = spi_SecsToMinutesColonSecsStr( nPosSecs )
		szTrkNr = ("trk%d"%(ii2+1,))
		data2 += (("%s"+"TRACK %02d AUDIO\n") % ( tabs2, ii2+1,))
		data2 += (("%s%s"+"TITLE \x22%s\x22\n") % ( tabs2, tabs2, szTrkNr,))
		data2 += (("%s%s"+"PERFORMER \x22%s\x22\n") % ( tabs2, tabs2, szTrkNr,))
		data2 += (("%s%s"+"INDEX 01 %s\n") % ( tabs2, tabs2, szMntSecs,))
	##print("data2: [\n%s]" % (data2,))
	return data2
##}

szHxIcue = (
	"CUE file either as (1) '--icue FILE', (2) as first loose file "+
	"with cue extension or (3) '--icue //eAutoCUEFile'. "+
	"In case of (3), user is asked to enter split size in minutes, then "+
	"new temporary CUE file is created and is used.")
szHxOdn = (
	"Optional output directory either as (1) '--odn DIR' "+
	"or (2) autogenerated from CUE location + timestamp subdir "+
	"(uses 'mkdir').")
szHxImf = (
	"Media file either as (1) '--imf FILE', (2) first loose "+
	"non cue file or (3) entry named 'FILE' found in cue file.")
szHxNoCli = "Do not show CLI menu and don't show any extra options."

## SPLIT_AV_FROM_CUE_PY
print("\n%s v1.4" % (os.path.basename(__file__).replace(".","_").upper(),))

g1z      = type("", (), {"group": (lambda self,g: ""),} )()
bAutoOud = 0
szFfm    = "ffmpeg"

szPathTxtFn = ("%s/path.cfg" % (os.path.dirname(__file__),))
if( os.path.isfile(szPathTxtFn) ):
	ln0 = os.path.expandvars( open(szPathTxtFn).read(1024).splitlines()[0].strip() )
	if( os.path.isfile(ln0) ):
		szFfm = ln0
	elif( len(ln0) ):
		os.environ["PATH"] = ("%s%s%s" % (ln0, os.pathsep, os.getenv("PATH"),) )

szStd = subprocess.check_output( ("%s -version" % (szFfm,)), shell=1 )
s = ( ( re.search("ffmpeg \\s+ version \\s+ ([^\\s]+)", szStd, re.I|re.X ) or g1z ).group(1) )
print("Using FFMPEG version: [%s]" % (s,) )

if( not len(s) ):
	print("ERROR: no working ffmpeg executable found.")
	print("       [%s]" % (szFfm,) )
	sys.exit(3)

prsr = optparse.OptionParser()
prsr.add_option("--icue", dest="icue", help=szHxIcue )
prsr.add_option("--imf", dest="imf", help=szHxImf )
prsr.add_option("--odn", dest="odn", help=szHxOdn )
prsr.add_option("--no_cli_menu", dest="no_cli_menu", action="store_true", help=szHxNoCli)
(optns, args) = prsr.parse_args()

szCue    = ( optns.icue if optns.icue else "" )
szImf    = ( optns.imf  if optns.imf  else "" )
szOud    = ( optns.odn  if optns.odn  else "" )
bCliMenu = ( 0 if int(bool(optns.no_cli_menu)) else 1 )

##print("no_cli_menu: %d" % (optns.no_cli_menu if optns.no_cli_menu else 0,))
##print("bCliMenu: %d" % (bCliMenu,))
##print("bool2:%d, int2:%d" % (bool(None), int(bool(None)),))

for a in args:
	ext2 = (os.path.splitext(a)[1]).strip(".").lower()
	if( ext2 == "cue" ):
		if( not len(szCue) ):
			szCue = a
	elif( ext2 == "txt" ):
		if( not len(szCue) ):
			szCue = a
	elif( not len(szImf) ):
		szImf = a
bAutoCueMode = 0
if( szCue == "//eAutoCUEFile" and os.path.isfile(szImf) ):
	bAutoCueMode = 1
	succ,msg,nLenMillis2 = spi_GetMediaLengthViaFfmpeg( szFfm, szImf )
	##print("Res: %d,'%s',%d" % (succ,msg,nLenMillis2,))
	if( not succ ):
		print("ERROR: Failed getting media length [HhduEdRlr]")
		print("       [%s]" % (msg,))
		sys.exit(2)
	ts2 = (int(round(time.time() * 1000)) / 1000)
	szCue = ("%s/%s_o%X.cue"  % ( os.path.dirname(szImf),
		(os.path.splitext(os.path.basename(szImf))[0].lstrip(".")), ts2 ))
	print("New CUE file name: [... %s]" % (szCue[-42:],))
	print("")
	print("Enter media split length in minutes (or use s## for seconds).")
	ans3 = raw_input("Input: ")
	nSpltLenMnts = int( next( ( m.group(1) for m in [re.search("^(\\d+)",ans3),] if m ), "0"))
	nSpltLenSecs = int( next( ( m.group(1) for m in [re.search("^s(\\d+)",ans3),] if m ), "0"))
	nSpltLenSecs = nSpltLenMnts * 60 + nSpltLenSecs
	if( not nSpltLenSecs ):
		print("ERROR: Zero AV length received [UpZYWWRuH]")
		sys.exit(2)
	nTotalLenSecs = int(nLenMillis2 / 1000)
	data3 = spi_GenerateCueDataGivenLen( nTotalLenSecs, nSpltLenSecs )
	##print("data3: [\n%s]" % (data3,))

	fp2 = open( szCue, "a+b")
	if( not fp2 ):
		print("ERROR: Failed opening cue file for write [tnSLp1KWU]")
		sys.exit(2)
	file.write( fp2, data3 )
	file.close( fp2 )
	##raw_input("....")

if( not szCue ):
	print("ERROR: no input CUE file (see '--icue FILE') [1wVojgC7Q]")
	sys.exit(2)
if( (not bAutoCueMode) and (not os.path.isfile(szCue)) ):
	print("ERROR: file '%s' not found [Kjy2OkDe]" % (os.path.splitext(szCue)[1].lstrip(".").upper(),) )
	sys.exit(2)
if( not szOud ):
	ts2 = int(round(time.time() * 1000)) / 1000
	bAutoOud = 1
	szOud = ("%s/out_%X" % ( os.path.dirname(szCue), ts2,) )
	print("INFO: autogenerated output directory to sub-dir-timestamp of the CUE file.")
	print("      [...%s]" % (szOud[-32:],) )
if( (not bAutoOud) and (not os.path.isdir(szOud)) ):
	##if( not sum( [bAutoOud, os.path.isdir(szOud),] ) ):
	print("ERROR: output dir not found [ioLguQFs]")
	sys.exit(2)

szCueExt = os.path.splitext(szCue)[1].lstrip(".").lower()
tracks2 = []; nErr = 0
if( szCueExt == "cue" ):
	print("Parsing CUE file...")
	(tracks2,szImf,nErr) = spi_ParseCUETracks( szCue, szImf )
elif( szCueExt == "txt" ):
	print("Parsing TXT file...")
	(tracks2,nErr) = spi_ParseTxtHmsTracks( szCue )
	print("Got %d tracks fronm TXT file." % ( len(tracks2),) )
	##sys.exit(255)
else:
	print("ERROR: bad input file, should be CUE or TXT [%s] [OGU28TU5]" % (szCueExt,))
	sys.exit(2)

print("")
print("Input CUE : [...%s]" % (szCue[-46:],) )
print("Input AV  : [...%s]" % (szImf[-46:],) )
print("Output dir: [...%s]" % (szOud[-46:],) )

tracks3 = []
for i in range(0, len(tracks2)):
	a = tracks2[i]
	n = ( tracks2[i+1] if ( i+1 < len(tracks2) ) else None )
	len2  = None
	tdBgn = datetime.timedelta( seconds = a["tm2"] )
	bgn2  = tdBgn.total_seconds()
	if n:
		tdEnd = datetime.timedelta( seconds = n["tm2"] )
		len2 = (tdEnd - tdBgn).total_seconds()
	if( len2 and len2 < 0 ):
		nErr += 1
		print("ERROR: negative length for track %d detected, ignoring." % (a["idx2"]+1,))
		print("       [%s] - [%s]" % (a["ath"], a["ttl"], ))
		continue
	tracks3.append( {"bgn2": bgn2, "len2": len2, "ath": a["ath"], "ttl": a["ttl"], "idx2": a["idx2"], } )




##hms = spi_SecsToHmsStr_( 203.28 )
##print("hms: [%s]" % (hms,))
##raw_input(".....")

print("\n"+"Preview:")
for i in range(0, len(tracks3)):
	a = tracks3[i]
	bOk = ( 1 if (not i) else ( 1 if (i+2 >= len(tracks3)) else 0 ) )
	if bOk:
		len2 = a["len2"]
		print("%5s: [%8s], bgn:[%-9s], [%8s], len:[%-9s]" %
				( ("First" if (not i) else ("#%02d" % (i+1,)) ),  ##a["idx2"]+1
						spi_SecsToHmsStr( a["bgn2"] ), str(a["bgn2"]),
						spi_SecsToHmsStr( len2 if len2 else 0 ), str(len2),) )

if( not szImf ):
	print("\n"+"ERROR: no input AV file (see '--imf FILE') [R9gBga]")
	sys.exit(2)

# using input RE string, searches for it inside subject and returns tuple containing
# two elements: extracted string and modified subject. if nothing is found, returns:
# tuple with 1st element empty and second set to original subject.
def spi_ExtractByRegex( szRe, szSubj, nGroup, szTrimchars ):
	mt5 = re.search( szRe, szSubj )
	if( mt5 and ( len( mt5.group( nGroup ) ) ) ):
		a = szSubj[ 0 : mt5.start( nGroup ) ].strip(szTrimchars)
		b = mt5.group( nGroup )
		c = szSubj[ mt5.end( nGroup ) :     ].strip(szTrimchars)
		return ( b, a+c, )
	return ( "", szSubj, )

ans2 = ""
if bCliMenu:
	print("\n--- Menu ---")
	print("b    --  hide ffmpeg stdout.")   ##bNoFfmStdou
	print("c    --  strip metadata.")   ##bStripMetadata
	print("d    --  stop on ffmpeg errors.")   ##bStopOnFfErr
	print("e    --  wait for confirm after each item.")   ##bCnfrmWaitNext
	print("f    --  no author and title for output file names.")   ##bNoAuthTitile
	print("[xx] --  output format, filename extension (eg. [mkv]).")   ##szNewFmt
	print("Selection:")
	ans2 = raw_input()

(szNewFmt,ans2,) = spi_ExtractByRegex("\\x5B(.+?)\\x5D", ans2, 1, "[]")  ##[] = 0x5B,0x5D
bNoFfmStdou    = ( 1 if ( 1+ans2.find("b") ) else 0 )
bStripMetadata = ( 1 if ( 1+ans2.find("c") ) else 0 )
bStopOnFfErr   = ( 1 if ( 1+ans2.find("d") ) else 0 )
bCnfrmWaitNext = ( 1 if ( 1+ans2.find("e") ) else 0 )
bNoAuthTitile  = ( 1 if ( 1+ans2.find("f") ) else 0 )
##bUndrscDownrn

if bAutoOud:
	print("INFO: Creating output dir.")
	os.mkdir( szOud )

szImfExt = (os.path.splitext(szImf)[1]).strip(".").lower()
szNewFmt = ( szNewFmt if szNewFmt else szImfExt )
aOuFmt   = ( (szNewFmt,szNewFmt,) if (szNewFmt != "mkv") else ("matroska","mkv",) )

for i in range(0, len(tracks3)):   ## for each track, executing ffmpeg command.
	a = tracks3[i]
	fnm2 = ""
	if( not bNoAuthTitile ):   ##bUndrscDownrn
		ath2 = re.sub("[^a-zA-Z0-9_]+", "_", a["ath"] )
		ttl2 = re.sub("[^a-zA-Z0-9_]+", "_", a["ttl"] )
		fnm2 = re.sub("_{2,}", "_", ("_%s_%s" % (ath2, ttl2,) ).rstrip("_") )[:64]
	szOuFnm  = ("%s/%03d%s.%s" % (szOud, i+1, fnm2, aOuFmt[1],))
	## ffmpeg -ss <secs.f> -t <secs.f> -f <fmt> -c:a copy -c:v copy ...
	## -hide_banner
	len2 = a["len2"]
	cmd2 = ("%s -loglevel 16 -i %s -f %s -c:a copy -c:v copy%s -ss%s%s%s %s" % (
				szFfm, ("\x22%s\x22" % szImf ), aOuFmt[0],
				(" -map_metadata -1" if bStripMetadata else "" ),
				(" %f" % a["bgn2"]),
				("" if (not len2) else (" -t %f" % (len2,)) ),
				("" if (not bNoFfmStdou) else (" 2>%s" % os.devnull) ),
				("\x22%s\x22" % szOuFnm),))
	print("\n"+"CMD: [%s]" % (cmd2,))
	print("%d/%d Running Ffmpeg...\n\n" % (i+1, len(tracks3),) ),
	rs2 = subprocess.call( cmd2, shell=1 )
	if rs2:
		nErr += 1
		print("ERROR: ffmpeg failed (code:%d, nErr:%d) [IQ57h6m]" % (rs2,nErr,))
		if bStopOnFfErr:
			raw_input("Continue...")
	if( bCnfrmWaitNext and (not rs2 or not bStopOnFfErr) ):
		raw_input("Continue...")


print("Done. (errors:%d)." % (nErr,) )










