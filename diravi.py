import dv_info
import sys
import dircache
import os

argc = len(sys.argv)
if argc == 1:
    sys.exit()
filelist = dircache.listdir(sys.argv[1])
for filename in filelist:
    filepath = sys.argv[1] + os.path.sep + filename
    if os.path.isfile(filepath):
        print filepath
        ret = dv_info.dvinfo(filepath)
        if ret:
            print ret[0]
        else:
            print "DV_INFO ERROR"
