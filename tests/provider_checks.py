"""Exercise external ModOptionsMenu API/options source, without its native UI hooks."""
from pathlib import Path
import hashlib,os

def run(Scenario):
    path=os.environ.get('HD2_MOD_OPTIONS_MENU_SOURCE')
    if not path:return None
    source=Path(path).read_bytes()
    def module(name):
        marker=b'mom_files.'+name+b' = function(...)'
        start=source.index(marker);end=source.index(b'\nmom_files.',start+len(marker))
        return source[start:end]
    s=Scenario()
    try:
        s.lua.execute(br'''
          local T={upper=string.upper,check=function()return true end,
            length=function(s)local _,n=s:gsub('[^\128-\191]','');return n end}
          mom={state={mods={},options={},option_count=0,values={},callbacks={},revision=0,
            saved={reckoning_120mm_language='2',reckoning_120mm_enabled='false'},
            pending={},pending_count=0,refused={},refused_count=0,queued={}},
            translation={T=T,tr=function(k)return k end},note=function()end,
            TEXT_TEMPLATE=123,MAX_MODS=112,MAX_ROWS=32,
            descriptor=function()return {},{} end}
          mom_files={}
        '''+module(b'options')+b'\n'+module(b'api')+b'''
          mom_files.options(mom);mom_files.api(mom);ModOptionsMenu=mom.api
        ''')
        s.tick();g=s.lua.globals();mom=g[b'mom'];state=mom[b'state'];api=mom[b'api']
        assert s.state[b'menu_registered'] is True and api[b'version']==3
        assert api[b'get'](b'reckoning_120mm_enabled') is True and api[b'get'](b'reckoning_120mm_language')==1
        assert len(state[b'mods'])==1 and len(state[b'mods'][1][b'order'])==2
        assert state[b'options'][b'reckoning_120mm_language'][b'label']==b'Language'
        mom[b'set_pending'](b'reckoning_120mm_enabled',False);s.tick()
        assert state[b'pending'][b'reckoning_120mm_enabled'] is False
        mom[b'set_pending'](b'reckoning_120mm_language',2)
        assert mom[b'apply_pending']()==2;s.tick();mom[b'translation'][b'refresh']()
        assert s.state[b'phase']==b'disabled' and s.bytes()==s.baseline
        assert state[b'options'][b'reckoning_120mm_enabled'][b'label']==b'Enable'
        assert state[b'mods'][1][b'title']==b'RECKONING 120MM BARRAGE'
        for _ in range(3):s.tick()
        assert len(state[b'callbacks'][b'reckoning_120mm_enabled'])==1
        print('PASS actual external ModOptionsMenu API 1 / version 3 registration, Apply, persistence and text refresh')
        return {'version':3,'source_sha256':hashlib.sha256(source).hexdigest(),
            'scope':'actual API/options modules; text service and native UI descriptor mocked; no native hook or in-game rendering'}
    finally:s.close()
