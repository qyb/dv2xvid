# -*- coding: cp936 -*-
import struct
import os
from ctypes import *
from ctypes.wintypes import *

def get_xvidconfig(s):
    fmtstring = 'i 4s 4s 260s i 4s'
    hsize = struct.calcsize(fmtstring)
    ret = list(struct.unpack(fmtstring, s[:hsize]))
    ret.append(s[hsize:])
    return ret
    
def get_xvidconfig_3532(s):
    fmtstring = 'i i i ' + \
                '260s ' + \
                'i i ' + \
                '260s ' + \
                'i ' + \
                '260s ' + \
                'i i ' + \
                '64s 64s ' + \
                'i i i i i i i i i i i ' + \
                'i i i i i ' + \
                'i 2304s i ' + \
                'i i i i ' + \
                'i i i i i i i i ' + \
                'i i i i i i i i i i i ' + \
                'i i i i i i i i i i i i i i i ' + \
                'i i i i i i i ' + \
                'i i i i i i i i i'
    #struct.calcsize(fmtstring) == 3532
    return struct.unpack(fmtstring, s)

def xvid_global():
    ### 定义结构体
    class xvid_gbl_info_t(Structure):
        _fields_ = [("version", c_int),
                    ("actual_version", c_int),
                    ("build", c_char_p),
                    ("cpu_flags", c_uint),
                    ("num_threads", c_int)]
    XVID_GBL_INFO = 1
    xvidcore = cdll.LoadLibrary(os.path.join(os.environ['WINDIR'],"system32\\xvidcore.dll"))
    xvid_global = xvidcore.xvid_global
    ### 构造 pinfo 结构体, 然后赋值
    pinfo = xvid_gbl_info_t()
    pinfo.version = ((((1)&0xff)<<16) | (((0)&0xff)<<8) | ((0)&0xff))
    x = c_voidp(0)
    y = c_voidp(0)
    ### 用 byref 传入指针
    if xvid_global(x, c_int(XVID_GBL_INFO), byref(pinfo), y) == 0:
        major_version = (pinfo.actual_version>>16)&0xff
        minor_version = (pinfo.actual_version>>8)&0xff
        patch_version = (pinfo.actual_version>>0)&0xff
        return [major_version, minor_version, patch_version, pinfo.build, pinfo.cpu_flags, pinfo.num_threads]
    else:
        return False

def xvid_config():
    xvidvfw = cdll.LoadLibrary(os.path.join(os.environ['WINDIR'],"system32\\xvidvfw.dll"))
    prototype = WINFUNCTYPE(LONG, DWORD, DWORD, UINT, LPARAM, LPARAM)
    paramflags = (1, "driverid", 0), \
                 (1, "hdriver", 0), \
                 (1, "umsg", 0), \
                 (1, "para1", 0), \
                 (1, "para2", 0)
    x = prototype(("DriverProc", xvidvfw), paramflags)
    configsize = x(umsg=0x5000)
    #print configsize
    did = x(umsg=0x0003)
    #print did
    config = create_string_buffer(configsize, configsize)
    pconfig = addressof(config)
    y = x(driverid=did, umsg=0x5000, para1=pconfig)
    s = string_at(pconfig, configsize)
    return s

if __name__ == "__main__":
    print xvid_global()
    configdata = xvid_config()
    print len(configdata)
    config = get_xvidconfig(configdata)
    print config[0], struct.unpack('i', config[1])[0], struct.unpack('i', config[2])[0], config[3], config[4], struct.unpack('i', config[5])[0]

'''
if configsize == 3532:
    # 1.1.0 and 1.2.0-dev
    config = get_xvidconfig_3532(s)
    pass
'''

'''
f = file('c:\\xvid.test', 'wb')
f.write(s)
f.close()
'''
