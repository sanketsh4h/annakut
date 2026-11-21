# Reads the iPhone's gravity vector (Apple MakerNote tag 0x0008, AccelerationVector)
# from JPEGs that sips converted from the original HEICs.
import sys, struct
from PIL import Image
def apple_accel(path):
    ex=Image.open(path).getexif()
    mn=ex.get_ifd(0x8769).get(0x927c)
    if mn is None: return None
    if not mn.startswith(b'Apple iOS'): return None
    # 'Apple iOS\0' + 2 bytes version + 'MM' ; offsets are relative to start of makernote
    bo='>' if mn[12:14]==b'MM' else '<'
    n=struct.unpack(bo+'H',mn[14:16])[0]
    for i in range(n):
        e=mn[16+12*i:28+12*i]
        tag,typ,cnt,off=struct.unpack(bo+'HHII',e)
        if tag==8 and typ==10 and cnt==3:
            vals=struct.unpack(bo+'6i',mn[off:off+24])
            return [vals[0]/vals[1],vals[2]/vals[3],vals[4]/vals[5]]
    return 'no tag 8'
for p in sys.argv[1:]:
    print(p.split('/')[-1], apple_accel(p))
