#!/usr/bin/env python
# -*- coding: utf-8 -*-

from socket import *

import thread
import threading
import time
import pickle
import signal 
import sys
import os
from optparse import OptionParser
# nacteni urllib
try:
    import urllib
except ImportError:
    print 'Module `urllib` not found. This module is needed for script running.'
    exit('Program terminated.')

VERSION = '0.2'
### where to download
download_dir = '/home/mihairu/downloader/'
suffix_dirs = {
    '.torrent'                      :    'torrents',
    '.avi|.mpeg|.mkv'               :    'videos',
    '.jpg|.jpeg|.png|.gif|.tiff'    :    'images',
    '.php|.py|.lua'                 :    'scripts',
    '.zip|.rar|.tar|.gz|.bz2'       :    'compressed',
    '.pdf|.doc|.odf'		    :    'documents',
    None                            :    'unsorted'
} 

#### socket settings
host = "localhost"
port = 21567
buf = 1024
addrA = (host,port)
addrB = (host,port+1)

#### list of urls to download
global queueURL
global successURL
global failURL

argURL = []
queueURL = []
successURL = []
failURL = []

### download info
global readedKb
global lengthKb
global downloadURL
global filenameURL
global directoryURL

### TODO
# pokud neexistuje slozka => vytvorit
# serializace dat pri vypnuti nebo killnuti => ulozeni historie queue a fail a success stahnuti
# pocet opakovanych pokusu az se oznaci jako fail
# nastaveni automatickeho mazani success url = countdown
# nastaveni poctu ukladanych url
# nastaveni resume => po nejakem case zkusit retry -- pak to hodit na konec queue a pak do fail
# MOZNA NAPICU: debug daemona => vymyslet jak ho po spusteni "zdaemonizovat" (debug bez daemonizace)

#### number of retries
retry = 5
#### try to resume file?
resume = True

#### how many seconds url will last in daemon (exiting of daemon
#### will kill all urls (maybe future release?)
#### e.g. countdown = 60*MINUTE || countdown = INFINITE
INFINITE = 0
INSTANTLY = 1
HALFMINUTE = 30
MINUTE = 2*HALFMINUTE
HOUR = 60*MINUTE
countdown = MINUTE

#### make socket
UDPSock = socket(AF_INET,SOCK_DGRAM)

parser = OptionParser(usage="Usage: %prog [options|urls]",
                      version="%%prog %s" % VERSION)
parser.add_option("--daemon", action="store_true", dest="DAEMON", default=False,
                  help="Start daemon")
parser.add_option("--queue", action="store_true", dest="QUEUE", default=False,
                  help="Show queue of urls")
parser.add_option("--fail", action="store_true", dest="FAIL", default=False,
                  help="Show failed downloads")
parser.add_option("--success", action="store_true", dest="SUCCESS", default=False,
                  help="Show success download")
parser.add_option("--del-queue", action="store_true", dest="DELQUEUE", default=False,
                  help="Clear queue list")
parser.add_option("--del-fail", action="store_true", dest="DELFAIL", default=False,
                  help="Clear fail list")
parser.add_option("--del-success", action="store_true", dest="DELSUCCESS", default=False,
                  help="Clear success list")
parser.add_option("--stats", action="store_true", dest="STATS", default=False,
                  help="Show current download information")
(options, argURL) = parser.parse_args()

def checkDownloadDirs():
    for suffix_dir in suffix_dirs:
        dir_to_check = download_dir + suffix_dirs[suffix_dir]
        if os.path.isdir(dir_to_check):
            continue
        else:
            os.mkdir(dir_to_check)

def getDownloadDir(filename):
    for suffix_dir in suffix_dirs:
        if suffix_dir != None:
            suffixs = suffix_dir.split('|')
            for suffix in suffixs:
                if filename.endswith(suffix):
                    temp_dir = download_dir + suffix_dirs[suffix_dir] + "/" + filename
                    break
    try: temp_dir
    except: temp_dir = download_dir + suffix_dirs[None] + "/" + filename

    return temp_dir

def countdownThread():
    global countlock
    global countdown

    countlock.acquire()
    if (countdown != INFINITE):
        while 1:
            print countdown
            countdown -= 1
            time.sleep(1)

def download(url):
    global threadlock

    global readedKb
    global lengthKb
    global downloadURL
    global filenameURL
    global directoryURL

    threadlock.acquire()

    try:
        print 'Opening url:', url
        webFile = urllib.urlopen(url)

        length = webFile.info().getheader("Content-Length")
        lengthKb = int(length) / 1024.0
        filename = url.split('/')[-1]
        
        print 'Downloading:',filename#, length
        localFile = open(getDownloadDir(filename), 'w')
        print 'Saving', url, 'to', getDownloadDir(filename)
        readed=0.0

        downloadURL = url
        filenameURL = filename
        directoryURL = getDownloadDir(filename)

        for line in webFile:
            readed+=len(line)
            readedKb = readed / 1024.0
            localFile.write(line)

    except:
        ### TODO pridat retry
        try:
            webFile.close()
            localFile.close()
        except: pass
        print 'FAIL'
        failURL.append(url)
        threadlock.release()
        return False

    webFile.close()
    localFile.close()

    successURL.append(url)
    threadlock.release()
    return True 

def loadProgram():
    global successURL
    global failURL
    global queueURL

    try:
        localFile = open('history', 'r')
        input = pickle.load(localFile)

        successURL = input[0]
        failURL = input[1]
        queueURL = input[2]
        return True
    except: return False

def exitProgram(signal, frame):
    global successURL
    global failURL
    global queueURL
    
    output = [successURL, failURL, queueURL]
    localFile = open('history', 'w')
    pickle.dump(output, localFile)
    localFile.close()
    sys.exit(0)

signal.signal(signal.SIGINT, exitProgram)

def getList(list, string):
    out = string + "\n"
    i = len(string)
    while (i>=0):
        out += '~'
        i-=1

    for x,url in enumerate(list):
        out = out + "\n" + str(x+1) + "\t" + url

    return out

def delList(list, string):
    global queueURL
    global failURL
    global successURL

    out = string
    if list == failURL:
        del(failURL)
    list = []
    return out

def delFail():
    global failURL
    out = "Deleting fail list"
    del(failURL)
    failURL = []
    return out

def delSuccess():
    global successURL
    out = "Deleting success list"
    del(successURL)
    successURL = []
    return out

def delQueue():
    global queueURL
    out = "Deleting queue list"
    del(queueURL)
    queueURL = []
    return out

def getStats():
    try:
        global readedKb
        global lengthKb
        global downloadURL
        global filenameURL
        global directoryURL
        
        out  = "Filename: " + str(filenameURL)
        out += "\n#urls:"
        out += "\nbytes: " + str(lengthKb)
        out += "\ndownloaded: " + str(readedKb)
        out += "\navg.speed:"
        out += "\nest.time:"
        out += "\nfolder: " + str(directoryURL)
        out += "\n#retry:"
        return out
    except:
        return "oops - get stats don't work right now"

"""
try:
    outfile=open(getURLName(url), "wb")
    fileName=outfile.name.split(os.sep)[-1]

    url, length=createDownload(url, proxies)
    if not length:
        length="?"

    print "Downloading %s (%s bytes) ..." % (url.url, length)
    if length!="?":
        length=float(length)
    bytesRead=0.0

    for line in url:
        bytesRead+=len(line)

        if length!="?":
            print "%s: %.02f/%.02f kb (%d%%)" % (
                fileName,
                bytesRead/1024.0,
                length/1024.0,
                100*bytesRead/length
                )

        outfile.write(line)

    url.close()
    outfile.close()
    print "Done"

"""

if options.DAEMON:
    checkDownloadDirs()
    loadProgram()
    UDPSock.bind(addrA)
    threadlock = thread.allocate_lock()
    countlock = thread.allocate_lock()
    while 1:
        ### start thread for countodwn
        #thread.start_new_thread(countdownThread, ())
        
        data,addrA = UDPSock.recvfrom(buf)
        if not data:
            pass
        else:
            if data == 'queue':
                UDPSock.sendto(getList(queueURL, 'Queued downloads'), addrB)
            elif data == 'success':
                UDPSock.sendto(getList(successURL, 'Success downloads'), addrB)
            elif data == 'fail':
                UDPSock.sendto(getList(failURL, 'Failed downloads'), addrB)
            elif data == 'delfail':
                UDPSock.sendto(delList(failURL, 'Deleting failed downloads'), addrB)
            elif data == 'delqueue':
                UDPSock.sendto(delQueue(), addrB)
            elif data == 'delsuccess':
                UDPSock.sendto(delSuccess(), addrB)
            elif data == 'stats':
                UDPSock.sendto(getStats(), addrB)
            else:
                print "Queing:", data
                queueURL.append([data, countdown])
                UDPSock.sendto('true', addrB)

        for url in queueURL:
            thread.start_new_thread(download, (url[0],))
            queueURL.remove(url)
else:
    UDPSock.bind(addrB)
    for url in argURL:
        UDPSock.sendto(url,addrA)

    #### LISTS
    if options.QUEUE:
        UDPSock.sendto('queue',addrA)
    if options.SUCCESS:
        UDPSock.sendto('success', addrA)
    if options.FAIL:
        UDPSock.sendto('fail',addrA)
    #### END OF LISTS

    #### DELETING
    if options.DELQUEUE:
        UDPSock.sendto('delqueue', addrA)
    if options.DELSUCCESS:
        UDPSock.sendto('delsuccess', addrA)
    if options.DELFAIL:
        UDPSock.sendto('delfail', addrA)
    #### END OF DELETING

    #### DOWNLOAD STATS
    if options.STATS:
        UDPSock.sendto('stats', addrA)
    #### END OF DOWNLOAD STATS
        
    data,addrB = UDPSock.recvfrom(buf)
    if not data:
        print 'No Data'
        pass
    else:
        print data

#    time.sleep(1) # processor
        
# Close socket
UDPSock.close()
