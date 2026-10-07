import pycdlib,os,sys
ISO="Lord of the Rings, The - The Fellowship of the Ring (USA).iso"
i=pycdlib.PyCdlib();i.open(ISO)
for r,ds,fs in i.walk(iso_path='/'):
    for f in fs:
        p=r.rstrip('/')+'/'+f
        if 'FELLOWSH.BIN' in p: continue
        out='work/orig'+p.split(';')[0]
        os.makedirs(os.path.dirname(out),exist_ok=True)
        i.get_file_from_iso(out,iso_path=p)
