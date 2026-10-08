"""Build a v18-discoverable data-only addon; validate the shipped Lua first."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.1.0'
RESOURCE='mods/reckoning_120mm/core'

def murmur64(data):
    mask=(1<<64)-1;m=0xc6a4a7935bd1e995;h=len(data)*m&mask
    for i in range(0,len(data)//8*8,8):
        k=int.from_bytes(data[i:i+8],'little')*m&mask;k^=k>>47;k=k*m&mask;h=(h^k)*m&mask
    tail=data[len(data)//8*8:]
    if tail:h=(h^int.from_bytes(tail,'little'))*m&mask
    h^=h>>47;h=h*m&mask;return h^(h>>47)

def patch(source):
    body=struct.pack('<II',len(source),2)+source;offset=192
    size=max(4096,(offset+len(body)+15)&~15);kind=0xa14e8dfa2cd117e2
    header=struct.pack('<4I',0xf0000011,1,1,0)+bytes(16)+struct.pack('<Q',size)+bytes(32)
    type_entry=struct.pack('<IIQQII',0,0,kind,1,16,16)
    entry=struct.pack('<7Q6I',murmur64(RESOURCE.encode()),kind,offset,0,0,0,0,len(body),0,0,16,16,0)
    return header+type_entry+entry+bytes(offset-len(header+type_entry+entry))+body+bytes(size-offset-len(body))

def manifest():
    return {'Version':1,'Guid':'1a076683-6d69-49ae-8877-ccb2fef315ec',
        'Name':'清算节 120mm 火力网 / Reckoning 120mm v'+VERSION,
        'Description':'恢复 2025 原生 HE/EMS 弹序：每轮 1 EMS + 6 高爆，基础 5 轮，散布字段 10。保留当前伤害及舰船升级。需要 Bingus Shared Loader v18。MODS 开关另需 ModOptionsMenu API1 / version2 或更新版本。支持 Steam build 25480438；尚未实机验证。',
        'Options':[{'Name':'清算节 120mm 火力网','Description':'MODS 中应用启用开关；只影响之后创建的火力网。关闭会恢复本模组拥有的配置。','Include':['Core']}]}

def build():
    subprocess.run([sys.executable,str(ROOT/'tests/test_runtime.py')],cwd=ROOT,check=True)
    source=(ROOT/'src/core.lua').read_bytes().replace(b'\r\n',b'\n')
    report=json.loads((ROOT/'validation/offline.json').read_text())
    assert report['source_sha256']==hashlib.sha256(source).hexdigest()
    name='Core/9ba626afa44a3aa3.patch_0'
    files={name:patch(source),name+'.stream':b'',name+'.gpu_resources':b'',
        'manifest.json':json.dumps(manifest(),ensure_ascii=True,indent=2).encode('ascii'),
        'VALIDATION.json':json.dumps(report,indent=2).encode('utf8')}
    output=ROOT/'dist'/f'Reckoning120mm_v{VERSION}.zip';output.parent.mkdir(exist_ok=True)
    tmp=output.with_suffix('.zip.tmp')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for key,value in sorted(files.items()):
            info=zipfile.ZipInfo(key,(2026,10,8,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,value)
    with zipfile.ZipFile(tmp) as z:
        assert z.testzip() is None
        assert all(z.read(k)==v for k,v in files.items())
    assert (ROOT/'src/core.lua').read_bytes().replace(b'\r\n',b'\n')==source
    tmp.replace(output);(ROOT/'manifest.json').write_bytes(files['manifest.json'])
    print(output);print('SHA256',hashlib.sha256(output.read_bytes()).hexdigest());return output

if __name__=='__main__':build()
