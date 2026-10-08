"""Execute the actual addon in LuaJIT with bounded Windows data-memory doubles."""
from pathlib import Path
import hashlib,json,os,re,struct,sys,tempfile
from lupa import luajit21
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'src/core.lua').read_bytes().replace(b'\r\n',b'\n')
FIXTURE=json.loads((ROOT/'tests/fixtures/native_2025.json').read_text())
BASE=0x180000000
Q=lambda n:struct.pack('<Q',n)
U=lambda n:struct.pack('<I',n)
F=lambda n:struct.pack('<f',n)

class Memory:
    def __init__(self):
        self.pages={};self.writes=[];self.protection={};self.fail=None;self.partial=None;self.deny=False
        self.restore_fail=0;self.reads=0
    def put(self,p,b):
        for i,v in enumerate(b):self.pages.setdefault((p+i)>>12,bytearray(4096))[(p+i)&4095]=v
    def read(self,p,n):
        self.reads+=1
        try:return bytes(self.pages[(p+i)>>12][(p+i)&4095] for i in range(n))
        except KeyError:return None
    def write(self,p,b):
        self.writes.append((p,b))
        if self.fail==p:self.fail=None;return False
        if self.partial==p:self.partial=None;self.put(p,b[:max(1,len(b)//2)]);return False
        self.put(p,b);return True
    def protect(self,p,v):
        if v==2 and self.restore_fail:self.restore_fail-=1;return 0
        self.protection[p>>12]=v;return 1
    def prot(self,p):return self.protection.get(p>>12,4)
    def query(self,p):
        start=p&~4095
        return struct.pack('<QQIIQIIII',start,start,4,0,4096,0x1000,32 if self.deny else self.prot(p),0x20000,0)

class Scenario:
    def __init__(self,cfg=None,bad_build=False,menu=False):
        self.temp=tempfile.TemporaryDirectory();self.local=Path(self.temp.name)
        self.logs=self.local/'CowboyBingus/Helldivers2/Logs';self.logs.mkdir(parents=True)
        self.cfg_path=self.logs/'Reckoning120mm.cfg'
        if cfg is not None:self.cfg_path.write_text(cfg,encoding='utf8')
        self.mem=Memory();self.lua=luajit21.LuaRuntime(encoding=None);self.replace_failure=False
        dos=bytearray(4096);dos[:2]=b'MZ';struct.pack_into('<I',dos,60,0x100);dos[0x100:0x104]=b'PE\0\0'
        struct.pack_into('<I',dos,0x108,0 if bad_build else 0x6ab3b43f);struct.pack_into('<I',dos,0x150,0x4744000)
        self.mem.put(BASE,dos)
        for a,h in re.findall(rb"\{(0x[0-9a-f]+),'([0-9a-f]+)'\}",SOURCE):self.mem.put(BASE+int(a,16),bytes.fromhex(h.decode()))
        self.root=0x60000000;self.table=0x61000000;self.strat=0x20000000;self.row=self.table+704+18*192
        self.mem.put(BASE+0x346bf98,Q(self.root));self.mem.put(self.root+0xf12a80,Q(self.table))
        self.mem.put(self.table-28,struct.pack('<I4sIIIII',0xcdbc43d8,b'LDLD',1,0xcdbc43d8,5120,1,0))
        self.baseline=bytes.fromhex(FIXTURE['baseline_row_hex'])
        self.mem.put(self.table,bytes(5120));self.mem.put(self.table+13*16,bytes.fromhex('b111d41e0bd03b2d')+U(18)+U(0))
        self.mem.put(self.row,self.baseline)
        raw=bytearray(400);struct.pack_into('<I',raw,0,136);struct.pack_into('<QQ',raw,0x98,0x40000000,1)
        self.mem.put(self.strat,raw);self.mem.put(0x40000000,bytes.fromhex('b111d41e0bd03b2d'))
        self.mem.put(BASE+0x37cb600+136*8,Q(self.strat));self.mem.put(BASE+0x21d4aa0+136*8,Q(0x41000000))
        self.mem.put(0x41000000,b'OrbitalStrike'+bytes(64))
        for t in (74,194,137):
            p=0x58000000+t*4096;raw=bytearray(160);struct.pack_into('<I',raw,0,t);raw[128:136]=bytes.fromhex('05a019313f4d392f')
            self.mem.put(p,raw);self.mem.put(BASE+0x37c7670+t*8,Q(p))
        g=self.lua.globals();g[b'pyread']=lambda p,n:self.mem.read(int(p),int(n));g[b'pywrite']=lambda p,b:self.mem.write(int(p),bytes(b))
        g[b'pyquery']=lambda p:self.mem.query(int(p));g[b'pyprot']=lambda p:self.mem.prot(int(p))
        g[b'pyprotect']=lambda p,n,v:self.mem.protect(int(p),int(v));g[b'pyreplace']=self.replace
        g[b'localpath']=str(self.local).encode()
        self.lua.execute(b'''
          local real=require('ffi');local ffi={};for k,v in pairs(real)do ffi[k]=v end
          local k={GetCurrentProcess=function()return real.cast('void *',1)end,
            GetModuleHandleA=function()return real.cast('void *',0x180000000)end}
          k.ReadProcessMemory=function(_,p,b,n,c)local s=pyread(tonumber(real.cast('uintptr_t',p)),n)
            if not s then c[0]=0;return 0 end;real.copy(b,s,n);c[0]=n;return 1 end
          k.WriteProcessMemory=function(_,p,b,n,c)local ok=pywrite(tonumber(real.cast('uintptr_t',p)),real.string(b,n));c[0]=ok and n or 0;return ok and 1 or 0 end
          k.VirtualQuery=function(p,b,n)local s=pyquery(tonumber(real.cast('uintptr_t',p)));real.copy(b,s,n);return n end
          k.VirtualProtect=function(p,n,v,old)local a=tonumber(real.cast('uintptr_t',p));old[0]=pyprot(a);return pyprotect(a,n,v)end
          k.MoveFileExA=function(a,b,flags)assert(flags==9);return pyreplace(a,b)end
          local aliases={};for name,fn in pairs(k)do aliases['reckoning120_'..name]=fn end
          ffi.load=function()return aliases end
          local old=require;require=function(n)if n=='ffi' then return ffi end;return old(n)end
          local getenv=os.getenv;os.getenv=function(k)if k=='LOCALAPPDATA' then return localpath end;return getenv(k)end
          print=function()end;calls=0;update=function(dt,x)calls=calls+1;return dt,x,42 end
        ''')
        if menu:self.load_menu()
        self.state=self.lua.eval(b'function(s)return assert(loadstring(s,"@mods/reckoning_120mm/core"))()end')(SOURCE)
    def replace(self,a,b):
        if self.replace_failure:return 0
        try:os.replace(os.fsdecode(a),os.fsdecode(b));return 1
        except OSError:return 0
    def tick(self):return self.lua.eval(b'function()return update(1.1,"preserved")end')()
    def cfg(self,s):self.cfg_path.write_text(s,encoding='utf8');self.tick()
    def bytes(self):return self.mem.read(self.row,192)
    def close(self):self.lua=None;self.temp.cleanup()
    def load_menu(self):
        self.lua.execute(b'''
          menu_state={values={reckoning_120mm_enabled=false,reckoning_120mm_language=2},options={},order={},callbacks={},pending={},sets=0}
          local s=menu_state;local api={api=1,version=3}
          function api.register_option(id,spec)
            assert(not s.options[id]);s.options[id]=spec;s.order[#s.order+1]=id
            if s.values[id]==nil then s.values[id]=spec.default end;return true end
          function api.get(id)return s.values[id]end
          function api.set(id,value)s.values[id]=value;s.pending[id]=nil;s.sets=s.sets+1;return true end
          function api.on_change(id,fn)assert(not s.callbacks[id]);s.callbacks[id]=fn;return true end
          function menu_apply(id,value)s.values[id]=value;return s.callbacks[id](value)end
          ModOptionsMenu=api
        ''')

def run_case(name,fn):
    s=Scenario()
    try:fn(s);print('PASS',name)
    finally:s.close()

def native_sequence(s):
    assert s.tick()==(1.1,b'preserved',42) and s.state[b'phase']==b'active'
    expected=bytearray(s.baseline)
    for ch in FIXTURE['delta']['changes']:
        expected[ch['offset']:ch['offset']+len(bytes.fromhex(ch['data']))]=bytes.fromhex(ch['data'])
    assert s.bytes()==bytes(expected)
    assert len(s.mem.writes)==3
    for _ in range(5):s.tick()
    assert len(s.mem.writes)==3
    # Only the 120mm row was modified; no executable, damage, projectile or stratagem writes.
    assert all(s.row<=p<p+len(b)<=s.row+192 for p,b in s.mem.writes)

def toggle(s):
    s.tick();s.cfg('enabled=0\nlanguage=en\n');assert s.bytes()==s.baseline and s.state[b'phase']==b'disabled'
    s.cfg('enabled=1\nlanguage=en\n');assert s.state[b'phase']==b'active';s.state[b'disable']();s.tick();assert s.bytes()==s.baseline

def foreign_writer(s):
    s.tick();s.mem.put(s.row+36,F(19));s.tick()
    assert s.state[b'phase']==b'stopped' and s.mem.read(s.row+36,4)==F(19)
    assert s.mem.read(s.row+4,4)==U(3) and s.mem.read(s.row+64,32)==s.baseline[64:96]

def stale_pointer(s):
    s.tick();n=len(s.mem.writes);s.mem.put(s.root+0xf12a80,Q(0x62000000));s.tick()
    assert s.state[b'phase']==b'stopped' and len(s.mem.writes)==n

def partial_failure(s):
    s.mem.partial=s.row+64;s.tick();assert s.state[b'phase']==b'stopped' and s.bytes()==s.baseline

def denied(s):
    s.mem.deny=True;s.tick();assert s.state[b'phase']==b'stopped' and s.bytes()==s.baseline and not s.mem.writes

def readonly(s):
    s.mem.protection[s.row>>12]=2;s.tick();assert s.state[b'phase']==b'active' and s.mem.prot(s.row)==2
    s.state[b'disable']();s.tick();assert s.bytes()==s.baseline and s.mem.prot(s.row)==2

def protection_failure(s):
    s.mem.protection[s.row>>12]=2;s.mem.restore_fail=1;s.tick()
    assert s.state[b'phase']==b'stopped' and s.bytes()==s.baseline and s.mem.prot(s.row)==2

def malformed(s):
    s.mem.put(s.row+4,U(8));s.tick();assert s.state[b'phase']==b'stopped' and not s.mem.writes

def header(s):
    s.mem.put(s.table-12,U(6000));s.tick();assert s.state[b'phase']==b'stopped' and not s.mem.writes

def missing_payload(s):
    s.mem.put(s.root+0xf12a80,Q(0));s.tick();assert s.state[b'phase']==b'waiting' and not s.mem.writes
    s.mem.put(s.root+0xf12a80,Q(s.table));s.tick();assert s.state[b'phase']==b'active'

def salvo_conflict(s):
    s.tick();s.mem.put(s.row+24,U(12));s.tick()
    assert s.state[b'phase']==b'stopped' and s.mem.read(s.row+24,4)==U(12)
    assert s.mem.read(s.row+4,4)==U(3) and s.mem.read(s.row+36,4)==F(27)

def restore_partial_failure(s):
    s.tick();s.mem.partial=s.row+64;s.cfg('enabled=0\n')
    assert s.state[b'phase']==b'stopped' and s.bytes()==s.baseline

def invalid_config(s):
    s.tick();s.cfg('language=invalid\nenabled=0\n');assert s.state[b'phase']==b'active'
    s.cfg('language=en\nenabled=no\n');assert s.state[b'config'][b'language']==b'zh'

def menu_case():
    s=Scenario(menu=True)
    try:
        s.tick();m=s.lua.globals()[b'menu_state']
        assert m[b'order'][1]==b'reckoning_120mm_language' and m[b'order'][2]==b'reckoning_120mm_enabled'
        assert m[b'values'][b'reckoning_120mm_enabled'] is True and m[b'values'][b'reckoning_120mm_language']==1
        s.lua.execute(b'menu_state.pending.reckoning_120mm_enabled=false')
        sets=m[b'sets'];s.tick();assert m[b'sets']==sets and m[b'pending'][b'reckoning_120mm_enabled'] is False
        writes=len(s.mem.writes);assert s.lua.globals()[b'menu_apply'](b'reckoning_120mm_language',2) is True;s.tick()
        assert len(s.mem.writes)==writes and m[b'options'][b'reckoning_120mm_enabled'][b'label']()==b'Enable'
        assert s.lua.globals()[b'menu_apply'](b'reckoning_120mm_enabled',False) is True;s.tick();assert s.bytes()==s.baseline
        saved=s.cfg_path.read_text();assert 'enabled=0' in saved and 'language=en' in saved
        s.replace_failure=True;result=s.lua.globals()[b'menu_apply'](b'reckoning_120mm_enabled',True)
        assert result[0] is False;s.tick();assert s.state[b'phase']==b'disabled'
    finally:s.close()
    s=Scenario(cfg=saved,menu=True)
    try:s.tick();assert s.state[b'phase']==b'disabled' and not s.mem.writes and s.state[b'config'][b'language']==b'en'
    finally:s.close()
    print('PASS menu cache, unapplied edits, language, persistence and save failure')

def main():
    cases=[native_sequence,toggle,foreign_writer,stale_pointer,partial_failure,denied,readonly,protection_failure,malformed,header,missing_payload,invalid_config,salvo_conflict,restore_partial_failure]
    for fn in cases:run_case(fn.__name__,fn)
    s=Scenario(bad_build=True)
    try:s.tick();assert s.state[b'phase']==b'stopped' and not s.mem.writes
    finally:s.close()
    print('PASS unsupported build');menu_case()
    from provider_checks import run
    provider=run(Scenario)
    sys.path.insert(0,str(ROOT/'tools'));from build import patch,murmur64,RESOURCE,ems_package
    archive=patch(SOURCE)
    magic,nt,nf,_=struct.unpack_from('<4I',archive)
    assert (magic,nt,nf)==(0xf0000011,2,2)
    types={struct.unpack_from('<Q',archive,72+i*32+8)[0]:struct.unpack_from('<Q',archive,72+i*32+16)[0] for i in range(nt)}
    entries={}
    for i in range(nf):
        r=struct.unpack_from('<7Q6I',archive,72+nt*32+i*80);name,kind,offset=r[:3];length=r[7]
        assert offset%16==0 and offset+length<=len(archive) and types[kind]==1
        entries[name]=(kind,archive[offset:offset+length])
    lua_kind,body=entries[murmur64(RESOURCE.encode())]
    assert lua_kind==0xa14e8dfa2cd117e2 and struct.unpack_from('<II',body)==(len(SOURCE),2)
    assert body[8:]==SOURCE and SOURCE.startswith(b'-- HD2-Addon: '+RESOURCE.encode())
    pkg_kind,pkg=entries[0x25b8cff26c7c0112]
    assert pkg_kind==0xad9c6d9ed1e5e77a and pkg==ems_package()
    fixture=json.loads((ROOT/'tests/fixtures/ems_packages_build25480438.json').read_text())
    base=bytes.fromhex(fixture['base_header_hex'])+b''.join(struct.pack('<QQ',int(t,16),int(n,16)) for t,n in fixture['base'])
    assert hashlib.sha256(base).hexdigest()==fixture['base_sha256']
    items=list(struct.iter_unpack('<QQ',pkg[16:]))
    assert struct.unpack_from('<I',pkg,8)[0]==len(items)==19 and len(set(items))==19
    assert all((int(t,16),int(n,16)) in items for t,n in fixture['base']+fixture['ems'])
    assert (0xa8193123526fad64,int(fixture['required_particle'],16)) in items
    assert (0x535a7bd3e650d799,int(fixture['required_audio_bank'],16)) in items
    assert pkg[:8]==base[:8] and pkg[12:16]==base[12:16]
    print('PASS native 120mm dependencies preserved and all EMS dependencies included')
    report={'status':'OFFLINE_PASSED','game_build':25480438,'source_sha256':hashlib.sha256(SOURCE).hexdigest(),
        'version':'0.1.1','test_groups':len(cases)+4+(1 if provider else 0),'ingame_tested':False,'multiplayer_tested':False,
        'ems_package_sha256':hashlib.sha256(pkg).hexdigest(),
        'package_fixture_sha256':hashlib.sha256((ROOT/'tests/fixtures/ems_packages_build25480438.json').read_bytes()).hexdigest(),
        'ems_dependency_count_added':len(items)-len(fixture['base']),
        'prior_user_feedback':'v0.1.0: projectile visible but EMS field visuals missing; stun not confirmed; own lobby',
        'external_menu_verification':provider,
        'policy':{'spread_field':10,'rounds_per_salvo':7,'base_salvos':5,'current_damage':True},
        'fixture_origin':FIXTURE['origin']}
    (ROOT/'validation').mkdir(exist_ok=True);(ROOT/'validation/offline.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('PASS archive identity and exact shipped source')

if __name__=='__main__':main()
