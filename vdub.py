import os
import struct
import base64
import sys
import stat
import math

import xvid
import dv_info

def write_lines(filename, lines):
    f = open(filename, "w")
    for line in lines:
        if line[-1] == '\n':
            f.write(line)
        else:
            f.write('%s\n' % line)
    f.close()
    
def audiovcf(tmp_avs, tmp_wav):
    ret = []
    ret.append('VirtualDub.Open("%s",0,0);' % tmp_avs.replace('\\', r'\\'))
    ret.append('VirtualDub.video.SetMode(0);')
    ret.append('VirtualDub.video.filters.Clear();')
    ret.append('VirtualDub.subset.Delete();')
    ret.append('VirtualDub.stream[0].SetMode(0);')
    ret.append('VirtualDub.stream[0].SaveWAV("%s");' % tmp_wav.replace('\\', r'\\'))
    return ret

def comptestvcf(tmp_avs, tmp_avi, data):
    ret = []
    ret.append('VirtualDub.Open("%s",0,0);' % tmp_avs.replace('\\', r'\\'))
    ret.append('VirtualDub.video.SetMode(1);')
    ret.append('VirtualDub.video.SetFrameRate(0,1);')
    ret.append('VirtualDub.video.SetIVTC(0,0,-1,0);')
    ret.append('VirtualDub.video.SetRange(0,0);')
    ret.append('VirtualDub.video.SetCompression(0x64697678,0,10000,0);')
    ret.append('VirtualDub.video.SetCompData(%d,"%s");' % (len(data), base64.standard_b64encode(data)))
    ret.append('VirtualDub.subset.Delete();')
    ret.append('VirtualDub.SaveAVI("%s");' % tmp_avi.replace('\\', r'\\'))
    return ret
    
def pass1vcf(tmp_avs, tmp_avi, data):
    ret = []
    ret.append('VirtualDub.Open("%s",0,0);' % tmp_avs.replace('\\', r'\\'))
    ret.append('VirtualDub.video.SetMode(1);')
    ret.append('VirtualDub.video.SetFrameRate(0,1);')
    ret.append('VirtualDub.video.SetIVTC(0,0,-1,0);')
    ret.append('VirtualDub.video.SetRange(0,0);')
    ret.append('VirtualDub.video.SetCompression(0x64697678,0,10000,0);')
    ret.append('VirtualDub.video.SetCompData(%d,"%s");' % (len(data), base64.standard_b64encode(data)))
    ret.append('VirtualDub.video.filters.Clear();')
    ret.append('VirtualDub.subset.Delete();')
    ret.append('VirtualDub.SaveAVI("%s");' % tmp_avi.replace('\\', r'\\'))
    return ret

def pass2vcf(tmp_avs, tmp_mp3, dst_avi, data):
    ret = []
    ret.append('VirtualDub.Open("%s",0,0);' % tmp_avs.replace('\\', r'\\'))
    ret.append('VirtualDub.video.SetMode(1);')
    ret.append('VirtualDub.video.SetFrameRate(0,1);')
    ret.append('VirtualDub.video.SetIVTC(0,0,-1,0);')
    ret.append('VirtualDub.video.SetRange(0,0);')
    ret.append('VirtualDub.video.SetCompression(0x64697678,0,10000,0);')
    ret.append('VirtualDub.video.SetCompData(%d,"%s");' % (len(data), base64.standard_b64encode(data)))
    ret.append('VirtualDub.video.filters.Clear();')
    ret.append('VirtualDub.subset.Delete();')
    ret.append('VirtualDub.RemoveInputStreams();')
    ret.append('VirtualDub.stream[0].SetSource("%s",0x00000202,0);' %  tmp_mp3.replace('\\', r'\\'))
    ret.append('VirtualDub.stream[0].SetMode(0);')
    ret.append('VirtualDub.stream[0].SetInterleave(1,500,2,0,0);')
    ret.append('VirtualDub.stream[0].SetClipMode(1,1);')
    ret.append('VirtualDub.stream[0].SetConversion(0,0,0,0,0);')
    ret.append('VirtualDub.stream[0].SetVolume();')
    ret.append('VirtualDub.stream[0].SetCompression();')
    ret.append('VirtualDub.SaveAVI("%s");' % dst_avi.replace('\\', r'\\'))
    return ret

from _winreg import *
def testAutoGK():
    try:
        autogk_reg = OpenKey(HKEY_LOCAL_MACHINE, "SOFTWARE\\AutoGK")
        InstallDir = QueryValueEx(autogk_reg, "InstallDir")
        return InstallDir[0]
        autogk_reg.Close()
    except:
        return False

def write_log(text):
    print text

def main(cmd, dst_avi, filelists, is16_9=False, targetsize=None, output=write_log):
    #print cmd, dst_avi, filelists
    execdir = os.path.dirname(cmd)
    if execdir == '':
        # after convert to .EXE by py2exe, maybe goto this case
        execdir = os.getcwd()
    #output('run path: %s' % execdir)
    
    autogk_dir = testAutoGK()
    if autogk_dir == False:
        base_dir = execdir
    else:
        base_dir = autogk_dir
        
    #now check necessary files
    xvidstring = xvid.xvid_config()
    xvidconf = xvid.get_xvidconfig(xvidstring)
    
    dvinfo_filter = os.path.join(execdir, "filters\\dvinfo.dll")
    deint_filter = os.path.join(base_dir, "filters\\LeakKernelDeint.dll")
    lame_cmd = os.path.join(base_dir, "tools\\lame\\lame.exe")
    vdub_cmd = os.path.join(base_dir, "VDubMod\\VirtualDubMod.exe")
    
    for i in [dvinfo_filter, deint_filter, lame_cmd, vdub_cmd]:
        if os.path.exists(i) == False:
            output('oops, %s not exist' % i)
            return

    dst_avi = os.path.normpath(dst_avi)
    dst_dir = os.path.dirname(dst_avi)
    tmp_dir = os.path.join(dst_dir, "d2x_tmp")
    if os.path.exists(tmp_dir):
        if os.path.isfile(tmp_dir):
            os.remove(tmp_dir)
    else:
        os.mkdir(tmp_dir)
    
    comptest_avs = os.path.join(tmp_dir, 'comptest.avs')
    comptest_vcf = os.path.join(tmp_dir, 'comptest.vcf')
    comptest_avi = os.path.join(tmp_dir, 'comptest.avi')
    audio_avs = os.path.join(tmp_dir, 'audio.avs')
    audio_vcf = os.path.join(tmp_dir, 'audio.vcf')
    movie_avs = os.path.join(tmp_dir, 'movie.avs')
    pass1_vcf = os.path.join(tmp_dir, 'pass1.vcf')
    pass2_vcf = os.path.join(tmp_dir, 'pass2.vcf')
    tmp_log = struct.pack('260s', os.path.join(tmp_dir, '_.log') + '\0')    
    tmp_wav = os.path.join(tmp_dir, '_.wav')
    tmp_mp3 = os.path.join(tmp_dir, '_.mp3')
    tmp_avi = os.path.join(tmp_dir, '_.avi')
    
    #tmp_avs = os.path.join(tmp_dir, '_.avs')
    #avs_filters = [dvinfo_filter, deint_filter]
    if is16_9 == False:
        comptest_res = (512, 384)
    else:
        comptest_res = (512, 288)
    
    seconds = 0
    for f in filelists:
        info = dv_info.dvinfo(f)
        if info:
            output("Verify ok: %s" % f)
            seconds += info[1].seconds
        else:
            output("Verify ko: %s" % f)
            filelists.remove(f)
    if seconds == 0:
        output("no data")
        return
    kbytes = seconds * 340
    #2720 kbps, 1/10 of original size
    if targetsize: kbytes = int(targetsize * 1000)
    
    avsFilelist = []
    for i in range(len(filelists)):
        avsFilelist.append(('file%d=\"' % i) + filelists[i] + '\"')

    avsFileConjoin = 'Directshowsource(file0)'
    for i in range(1,len(filelists)):
        avsFileConjoin += ' + Directshowsource(file%d)' % i
    
    write_lines(audio_avs, avsFilelist + [avsFileConjoin])
    write_lines(audio_vcf, audiovcf(audio_avs, tmp_wav))
    output('%s /x /s"%s"' % (vdub_cmd, audio_vcf))
    ret = os.spawnl(os.P_WAIT, vdub_cmd, "VirtualDubMod.exe", "/x", '/s"%s"' % audio_vcf)
    if ret != 0:
        output('spawn wav error: %d' % ret)
        return ret
    
    output('%s -b 96 -h "%s" "%s"' % (lame_cmd, tmp_wav, tmp_mp3))
    ret = os.spawnl(os.P_WAIT, lame_cmd, "lame.exe", "-b", "96", "-h", '"%s"' % tmp_wav, '"%s"' % tmp_mp3)
    if ret != 0:
        output('spawn mp3 error: %d' % ret)
        return ret
    
    mp3size = os.stat(tmp_mp3)[stat.ST_SIZE]
    output("MP3 size(bytes): %d" % mp3size)
    
    CompData_comptest = struct.pack('<i', 0) + xvidconf[1] + xvidconf[2] + tmp_log + struct.pack('<i', 0) + struct.pack('<i', 200) + xvidconf[6]
    CompData_pass1 = struct.pack('<i', 1) + xvidconf[1] + struct.pack('<i', kbytes) + tmp_log + struct.pack('<i', 0) + xvidconf[5] + xvidconf[6]
    CompData_pass2 = struct.pack('<i', 2) + xvidconf[1] + struct.pack('<i', kbytes) + tmp_log + struct.pack('<i', 0) + xvidconf[5] + xvidconf[6]
    
    avsFileConjoin = 'Directshowsource(file0).DVInfo(file0,"rec_time",size=32,text_color=$FFFFFF,align=3)'
    for i in range(1,len(filelists)):
        avsFileConjoin += ' + Directshowsource(file%d).DVInfo(file%d,"rec_time",size=32,text_color=$FFFFFF,align=3)' % (i,i)
    
    comptest_multiple = int(seconds / 10) + 1
    if comptest_multiple > 20:
        comptest_multiple = 20
    output("comptest resolution = %d x %d" % comptest_res)
    KernelDeInt = 'LeakKernelDeInt(order=1,sharp=true)'
    LanczosResize = 'LanczosResize(%d,%d)' % comptest_res
    SelectRangeEvery = 'SelectRangeEvery(%d,%d)' % (15*comptest_multiple, 15)
    
    write_lines(comptest_avs, ['LoadPlugin("%s")' % dvinfo_filter, 'LoadPlugin("%s")' % deint_filter] + avsFilelist + [avsFileConjoin, KernelDeInt, LanczosResize, SelectRangeEvery])
    write_lines(comptest_vcf, comptestvcf(comptest_avs, comptest_avi, CompData_comptest))
    output('%s /x /s"%s"' % (vdub_cmd, comptest_vcf))
    ret = os.spawnl(os.P_WAIT, vdub_cmd, "VirtualDubMod.exe", "/x", '/s"%s"' % comptest_vcf)
    if ret != 0:
        output('spawn comptest error: %d' % ret)
        return ret
    
    
    comptest_size = os.stat(comptest_avi)[stat.ST_SIZE]
    comptest_value = float(kbytes*1000)/(comptest_size * comptest_multiple)
    output('comptest value is: %.2f%%' % (comptest_value*100))
    multiple = math.sqrt(comptest_value / 0.7)
    #predict compressibility is 70%
    if is16_9 == False:
        unit_minw = 8
        unit_minh = 6
    else:
        unit_minw = 32
        unit_minh = 18
    resolution = int(comptest_res[0] * multiple / unit_minw)
    width = resolution * unit_minw
    height = resolution * unit_minh
    if width > 720:
        print width
        x = width / 720.0
        print x
        y = math.pow(x, 2)
        print y
        s = (kbytes / math.pow(width / 720.0, 2)) / 1000
        print s
        output('oops, reduce your target size to less than %.2f MB' % s)
        return
    #unit_min cannot be set to 4x3, It will cause Vdub error
    output('choose %dx%d, predict compressibility is %.2f%%' % (width,height,comptest_value*pow(float(comptest_res[0])/width,2)*100))

    LanczosResize = 'LanczosResize(%d,%d)' % (width, height)
    write_lines(movie_avs, ['LoadPlugin("%s")' % dvinfo_filter, 'LoadPlugin("%s")' % deint_filter] + avsFilelist + [avsFileConjoin, KernelDeInt, LanczosResize])
    write_lines(pass1_vcf, pass1vcf(movie_avs, tmp_avi, CompData_pass1))
    output('%s /x /s"%s"' % (vdub_cmd, pass1_vcf))
    ret = os.spawnl(os.P_WAIT, vdub_cmd, "VirtualDubMod.exe", "/x", '/s"%s"' % pass1_vcf)
    if ret != 0:
        output('spawn pass1 error: %d' % ret)
        return ret
    
    write_lines(pass2_vcf, pass2vcf(movie_avs, tmp_mp3, dst_avi, CompData_pass2))
    output('%s /x /s"%s"' % (vdub_cmd, pass2_vcf))
    ret = os.spawnl(os.P_WAIT, vdub_cmd, "VirtualDubMod.exe", "/x", '/s"%s"' % pass2_vcf)
    if ret != 0:
        output('spawn pass2 error: %d' % ret)
        return ret
    output('compress %s ok' % dst_avi)
    return 0

if __name__ == "__main__":
    argc = len(sys.argv)
    if (argc < 4):
        print "usage: %s [dst_avi] [files...] [AR16:9 0/1 -> 4:3/16:9]" % (sys.argv[0])
    else:
        xfiles = []
        for i in range(2, argc-1):
            xfiles.append(sys.argv[i])
        main(sys.argv[0], sys.argv[1], xfiles, int(sys.argv[argc-1]))
