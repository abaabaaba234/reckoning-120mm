"""Build a v18-discoverable data-only addon; validate the shipped Lua first."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.1.1'
RESOURCE='mods/reckoning_120mm/core'

def murmur64(data):
    mask=(1<<64)-1;m=0xc6a4a7935bd1e995;h=len(data)*m&mask
    for i in range(0,len(data)//8*8,8):
        k=int.from_bytes(data[i:i+8],'little')*m&mask;k^=k>>47;k=k*m&mask;h=(h^k)*m&mask
    tail=data[len(data)//8*8:]
    if tail:h=(h^int.from_bytes(tail,'little'))*m&mask
    h^=h>>47;h=h*m&mask;return h^(h>>47)

def ems_package():
    fixture=json.loads((ROOT/'tests/fixtures/ems_packages_build25480438.json').read_text())
    # Preserve every original dependency and header field; add the native EMS
    # package's missing references. No particles/audio/game assets are copied.
    items=sorted({tuple(x) for x in fixture['base']+fixture['ems']})
    header=bytearray.fromhex(fixture['base_header_hex']);struct.pack_into('<I',header,8,len(items))
    return bytes(header)+b''.join(struct.pack('<QQ',int(t,16),int(n,16)) for t,n in items)

def patch(source):
    lua_kind=0xa14e8dfa2cd117e2;package_kind=0xad9c6d9ed1e5e77a
    resources=[(murmur64(RESOURCE.encode()),lua_kind,struct.pack('<II',len(source),2)+source),
               (0x25b8cff26c7c0112,package_kind,ems_package())]
    kinds=sorted({r[1] for r in resources});offset=(72+len(kinds)*32+len(resources)*80+15)&~15
    entries=[];payload=bytearray()
    for name,kind,body in resources:
        entries.append(struct.pack('<7Q6I',name,kind,offset+len(payload),0,0,0,0,len(body),0,0,16,16,0))
        payload.extend(body);payload.extend(bytes((-len(payload))%16))
    size=max(4096,offset+len(payload))
    header=struct.pack('<4I',0xf0000011,len(kinds),len(resources),0)+bytes(16)+struct.pack('<Q',size)+bytes(32)
    types=b''.join(struct.pack('<IIQQII',0,0,k,1,16,16) for k in kinds)
    tables=header+types+b''.join(entries)
    return tables+bytes(offset-len(tables))+payload+bytes(size-offset-len(payload))

def manifest():
    return {'Version':1,'Guid':'1a076683-6d69-49ae-8877-ccb2fef315ec',
        'Name':'清算节 120mm 火力网 / Reckoning 120mm v'+VERSION,
        'Description':'恢复 2025 原生 HE/EMS 弹序，并为 120mm 资源包补齐原生轨道 EMS 的粒子和音频依赖。每轮 1 EMS + 6 高爆，基础 5 轮，散布字段 10。保留当前伤害及舰船升级。需要 Bingus Shared Loader v18。MODS 开关另需 ModOptionsMenu API1 / version2 或更新版本。支持 Steam build 25480438；此修复尚未实机验证。',
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
