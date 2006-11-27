import struct
import sys
import datetime

offset = []
fourcc = ''
super_index = ''
dvformat = 0 # 1=PAL; 2=NTSC


def readChunk(file, size, depth):
    global first_offset
    global last_offset
    global fourcc
    global super_index
    global dvformat
    cur_stream = ''
    s = file.read(8)
    while 8 == len(s):
        size -= 8
        head = struct.unpack('<4sI', s)
        if head[0] == 'LIST':            
            listType = file.read(4)
            size -= 4
            listSize = head[1] - 4
#            print ' '*depth, 'LIST ', head[1], listType
            if listType == 'movi':
                movi_offset = file.tell() + 4
#                print 'MOVI OFFSET: ', movi_offset
                file.seek(listSize, 1)
            elif listType == 'INFO':
                file.seek(listSize, 1)
            else:
                xread = readChunk(file, listSize, depth+1)
                if xread < 0:
                    return -1
            size -= listSize
        elif head[0] == 'JUNK':
#            print ' '*depth, 'JUNK', head[1]
            file.seek(head[1], 1)
            size -= head[1]
        else:
            page = (head[1] - 1)/4
            chunksize = (page + 1) * 4
            chunksize = head[1] # bugfix for 0.8.1
#            print ' '*depth, head[0], head[1], chunksize
            if head[0] == 'avih':
                s = file.read(chunksize)
                s = s[0:40]
                avih = struct.unpack('<10I', s)
                if avih[9] == 576:
                    dvformat = 1
                elif avih[9] == 480:
                    dvformat = 2
#                print "AVI SUMMARY: %d frames, %dx%d" % (avih[4], avih[8], avih[9])
            elif head[0] == 'strh':
                s = file.read(chunksize)
                s = s[0:8]
                strh = struct.unpack('<4s4s', s)
                cur_stream = strh[0]
                if strh[0] == 'vids':
                    fourcc = strh[1]
#                print 'STREAM HEADER: ', strh[0], strh[1]
            elif head[0] == 'idx1':
                s = file.read(chunksize)
                pagesize = (chunksize / 16) * 16;
                for i in range(0, pagesize, 16):
                    frame = s[i:i+16]
                    idx1 = struct.unpack('<4s3I', frame)
#                    print idx1[0], idx1[1], idx1[2], idx1[3]
                    if idx1[0] == '00db':
                        offset.append(idx1[2] + movi_offset)
            elif head[0] == 'indx':
                s = file.read(24)
                indx_h = struct.unpack('<h2BI4s3I', s)
#                print cur_stream, indx_h
#                print chunksize - 24, 4 * indx_h[0]
                s = file.read(chunksize - 24)
                if cur_stream == 'vids' and indx_h[0] == 4:
                    '''AVI Super Index Chunk for VIDEO'''
                    super_index = s[0:16*indx_h[3]]
            else:
                file.seek(chunksize, 1)
            size -= chunksize
        if size <= 0:
            return size
        s = file.read(8)

def readtime(avifile, offset):
    global dvformat
    dt = None
    if dvformat == 1:
        tracks = 12
    elif dvformat == 2:
        tracks = 10
    else:
        tracks = 0
    
    avifile.seek(offset, 0)
    for i in range(tracks):
        s = avifile.read(12000)
        frame = struct.unpack('12000B', s)
        DV_Header = frame[0:80]
        DV_Subcode = [frame[80:160], frame[160:240]]
        DV_Vaux = [frame[240:320], frame[320:400], frame[400:480]]
        VAUX_Packet = []
        for j in range(15):
            VAUX_Packet.append(DV_Vaux[2][3+5*j:8+5*j])
        apt = DV_Header[4] & 0x07
        magic = VAUX_Packet[10]
        if magic[0] != 0x61: #libavformat:dv.c:dv_video_control
            continue
        aspect = magic[2] & 0x07
        is16_9 = ((aspect == 0x02) or ((not apt) and (aspect == 0x07)))
#        print aspect, apt, is16_9
        time = VAUX_Packet[11] + VAUX_Packet[12]
        
        '''
        vaux_offset = offset + 80;
        vaux_offset += 80 * 2;
        vaux_offset += 80 * 2 + 48;
        avifile.seek(vaux_offset, 0)
        
        s = avifile.read(10)
        magic = struct.unpack('10B', s)
        #if magic[5] != 0x61 ....    libavformat:dv.c:dv_video_control
        print 'aaaa', magic[7] & 0x07
        
        s = avifile.read(10)
        time = struct.unpack('10B', s)
        '''
        day = time[2]
        month = time[3]
        year = time[4]
        second = time[7]
        minute = time[8]
        hour = time[9]
        year = (year & 0xf) + 10 * ((year >> 4) & 0xf)
        month = (month & 0xf) + 10 * ((month >> 4) & 0x1)
        day = (day & 0xf) + 10 * ((day >> 4) & 0x3)
        hour = (hour & 0xf) + 10 * ((hour >> 4) & 0x3)
        minute = (minute & 0xf) + 10 * ((minute >> 4) & 0x7)
        second = (second & 0xf) + 10 * ((second >> 4) & 0x7)
        if year < 25:
            year += 2000
        else:
            year += 1900
#        print year, month, day, hour, minute, second

        try:
            dt = datetime.datetime(year, month, day, hour, minute, second)
        except ValueError:
            #offset += 12000
            continue
        break
    if dt == None:
        return None
    return ["%4d-%02d-%02d %02d:%02d:%02d" % (year,month,day,hour,minute,second), dt, is16_9]
    
def dvinfo(filename):
    global offset
    global fourcc

    try:
        avifile = open(filename, 'rb')
    except:
        return None

    s = avifile.read(12)
    try:
        head = struct.unpack('<4sI4s', s)
    except:
        return None
    if head[0] != 'RIFF' or head[2] != 'AVI ':
        return None
    while True:
#        print head[1]-4
        xread = readChunk(avifile, head[1]-4, 0)
#        print '\n\n\n'
        if xread < 0:
            return None
        s = avifile.read(12)
        if 0 == len(s):
            break
        try:
            head = struct.unpack('<4sI4s', s)
        except:
            return None
        if head[0] != 'RIFF' or head[2] != 'AVIX':
            return None

    if fourcc != 'dvsd':
        avifile.close
        return None

    if super_index != '':
        offset = []
#        print len(super_index)
        for i in range(0, len(super_index), 16):
            sindex = struct.unpack('q2I', super_index[i:i+16])
#            print sindex
            avifile.seek(sindex[0], 0)
            si_header = struct.unpack('<4sIh2BI4sqI', avifile.read(32))
            if si_header[1] != sindex[1]-8:
                break
            if si_header[2] == 2:
                '''AVI Standard Index Chunk'''
#                print si_header[5]
                for j in range(0, si_header[5]):
                    aindex = struct.unpack('<2I', avifile.read(8))
                    offset.append(aindex[0] + si_header[7])
#        print offset

    if len(offset) < 2:
        avifile.close
        return None

    for i in offset:
        start = readtime(avifile, i)
        if start != None:
            break
    offset.reverse()
    for i in offset:
        end = readtime(avifile, i)
        if end != None:
            break;
    if start[2] != end[2]:
        return None
    is16_9 = start[2]
    diff = end[1] - start[1]
    start = start[0].split(' ')
    end = end[0].split(' ')
    avifile.close
    if start[0] == end[0]:
        return ["%s %s-%s" % (start[0], start[1], end[1]), diff, is16_9]
    else:
        return ["%s %s --- %s %s" % (start[0], start[1], end[0], end[1]), diff, is16_9]

def main():
    argc = len(sys.argv)
    if argc > 1:
        ret = dvinfo(sys.argv[1])
        if ret:
            print 'DV DATETIME:', ret[0]
    else:
        print "usage: %s [avi filename]" % (sys.argv[0])

if __name__ == "__main__":
    main()
