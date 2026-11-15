#!/usr/bin/env python3
"""Linux 设置窗口生命周期回归（需要 debug 构建、Xvfb、xdotool、ImageMagick）。

运行：xvfb-run -a -s '-screen 0 1024x768x24' dbus-run-session -- python3 tool/settings_window_smoke.py
使用临时配置，不访问用户密钥；直接调用托盘／关闭回调，验证三轮设置与胶囊切换。
这里验证窗口显示和模式恢复，不发起录音或云端请求。
"""
import os, pathlib, subprocess, time, tempfile, json
root=pathlib.Path(tempfile.mkdtemp(prefix='nextalk-deepseek-ui-'))
env=os.environ.copy()
for key, leaf in [('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_RUNTIME_DIR','runtime')]:
    path=root/leaf;path.mkdir(mode=0o700);env[key]=str(path)
env['NEXTALK_NO_TRAY']='1'
env['DEEPSEEK_API_KEY']=''
env['GDK_BACKEND']='x11'
env['LANG']='en_US.UTF-8'
conf=root/'config'/'nextalk';conf.mkdir()
(conf/'settings.yaml').write_text('model:\n  engine: deepseek\n  deepseek:\n    api_key: ""\n')
app=str(pathlib.Path(__file__).resolve().parents[1]/'build/linux/x64/debug/bundle/voice_capsule')
import urllib.request, urllib.parse, re
print('测试记录目录：',root,flush=True)
with (root/'app.log').open('w') as log:
    process=subprocess.Popen([app],env=env,stdout=log,stderr=subprocess.STDOUT)
    try:
        def visible():
            return subprocess.run(['xdotool','search','--onlyvisible','--name','Nextalk'],env=env,capture_output=True).returncode==0
        for _ in range(240):
            if visible(): break
            time.sleep(.25)
        time.sleep(1)
        uri=re.search(r'The Dart VM service is listening on (http://\S+)',(root/'app.log').read_text()).group(1)
        def rpc(method,**params):
            with urllib.request.urlopen(uri+method+'?'+urllib.parse.urlencode(params),timeout=5) as response:
                data=json.load(response)
                if 'error' in data: raise RuntimeError(str(data))
                return data['result']
        isolate=rpc('getVM')['isolates'][0]['id']
        libs=rpc('getIsolate',isolateId=isolate)['libraries']
        def evaluate(file,expression):
            lib=rpc('getObject',isolateId=isolate,objectId=next(x['id'] for x in libs if x['uri'].endswith(file)))
            cls=rpc('getObject',isolateId=isolate,objectId=next(x['id'] for x in lib['classes'] if x['name']==expression.split('.')[0]))
            instance=rpc('getInstances',isolateId=isolate,objectId=cls['id'],limit=1)['instances'][0]['id']
            obj=rpc('getObject',isolateId=isolate,objectId=instance)
            if expression.endswith('show()') or expression.endswith('hide()'):
                return rpc('invoke',isolateId=isolate,targetId=instance,selector=expression.split('.')[2].split('(')[0],argumentIds='[]',disableBreakpoints='true')
            callback=next(f['value']['id'] for f in obj['fields'] if f['decl']['name']==expression.split('.')[2].split('?')[0])
            return rpc('invoke',isolateId=isolate,targetId=callback,selector='call',argumentIds='[]',disableBreakpoints='true')
        print('first visible:',visible(),flush=True)
        for i in range(3):
            evaluate('services/window_service.dart','WindowService.instance.onConfigurationClose?.call()')
            time.sleep(.7)
            print('closed:',not visible(),flush=True)
            evaluate('services/window_service.dart','WindowService.instance.show()')
            time.sleep(.5)
            assert visible(), 'capsule not visible'
            ids=subprocess.check_output(['xdotool','search','--onlyvisible','--name','Nextalk'],env=env,text=True).split()
            hints=subprocess.check_output(['xprop','-id',ids[-1],'_NET_WM_WINDOW_TYPE','_MOTIF_WM_HINTS','WM_HINTS'],env=env,text=True)
            assert '_NET_WM_WINDOW_TYPE_UTILITY' in hints, hints
            assert 'False' in hints, hints
            print('capsule visible, utility, no focus:',True,flush=True)
            subprocess.run(['import','-window','root',str(root/'capsule-restored.png')],env=env,check=True)
            evaluate('services/window_service.dart','WindowService.instance.hide()')
            time.sleep(.3)
            evaluate('services/tray_service.dart','TrayService.instance.onShowSettings?.call()')
            time.sleep(2)
            print('reopen',i+1,'visible:',visible(),flush=True)
            if visible():
                wid=subprocess.check_output(['xdotool','search','--onlyvisible','--name','Nextalk'],env=env,text=True).split()[-1]
                geometry=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],env=env,text=True)
                g=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
                assert 0 <= int(g['X']) <= 1024-int(g['WIDTH']), geometry
                assert 0 <= int(g['Y']) <= 768-int(g['HEIGHT']), geometry
                print('settings inside display:', True, flush=True)
            if not visible():
                cls=next(x for x in rpc('getObject',isolateId=isolate,objectId=next(x['id'] for x in libs if x['uri'].endswith('app/nextalk_app.dart')))['classes'] if x['name']=='_NextalkAppState')
                refs=rpc('getInstances',isolateId=isolate,objectId=cls['id'],limit=1)['instances']
                obj=rpc('getObject',isolateId=isolate,objectId=refs[0]['id'])
                print([(f['decl']['name'],f['value'].get('valueAsString')) for f in obj['fields'] if f['decl']['name'] in ['_windowTransition','_settingsOpen']],flush=True)
                raise RuntimeError('reopen failed')
        subprocess.run(['import','-window','root',str(root/'settings-reopened.png')],env=env,check=True)
    finally:
        process.terminate();process.wait(timeout=5)
