import numpy as np
def read_ply(path):
    with open(path,'rb') as f:
        props=[];n=0
        while True:
            l=f.readline().decode().strip()
            if l.startswith('element vertex'): n=int(l.split()[2])
            elif l.startswith('property'):
                t,name=l.split()[1:3]; props.append((name,{'float':'<f4','uchar':'u1','int':'<i4','uint':'<u4'}[t]))
            elif l=='end_header': break
        return np.frombuffer(f.read(n*np.dtype(props).itemsize),dtype=props,count=n)
