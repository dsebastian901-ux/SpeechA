"""Pruebas reales de CMD; requieren Windows y un Python con requirements.

Ejecutar: python tests/test_startup_windows.py
Los entornos temporales usan el Python ya instalado; no descargan paquetes.
El main de prueba importa CustomTkinter y registra el intérprete realmente usado.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

APP=Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name=='nt','Requiere CMD y Python de Windows.')
class WindowsStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe=subprocess.run([sys.executable,str(APP/'tools/check_startup_environment.py')],capture_output=True)
        if probe.returncode:
            raise unittest.SkipTest('El Python de pruebas necesita los componentes locales de requirements.txt.')
        cls.support=tempfile.TemporaryDirectory(prefix='mrs-startup-environments-')
        cls.good=Path(cls.support.name)/'ready'
        cls.bad=Path(cls.support.name)/'incomplete'
        for directory,extra in [(cls.good,['--system-site-packages']),(cls.bad,[])]:
            subprocess.run([sys.executable,'-m','venv','--without-pip',*extra,str(directory)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.support.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='mrs repo con espacios (prueba)-')
        self.repo=Path(self.temp.name)
        self.app=self.repo/'proyecto/MRS_Speech_Analytics_v3.6.19_Revision'
        self.app.mkdir(parents=True)
        (self.app/'tools').mkdir()
        for filename in ['ENTORNO_MRS.bat','INSTALAR.bat','INICIAR_MRS.bat']:
            shutil.copyfile(APP/filename,self.app/filename)
        shutil.copyfile(APP/'tools/check_startup_environment.py',self.app/'tools/check_startup_environment.py')
        self.write_main(0)
        self.env=dict(os.environ)
        for key in list(self.env):
            if key.upper()in{'VIRTUAL_ENV','CONDA_PREFIX','PYTHONHOME','PYTHONPATH','MRS_PYTHON','MRS_READY','MRS_PYTHON_EXE','MRS_PYTHON_VERSION'}:
                self.env.pop(key,None)
        self.env.update(MRS_NO_PAUSE='1',PYTHONDONTWRITEBYTECODE='1')
        # Solo el Python incompleto en PATH, sin py.exe ni Python global.
        self.env['PATH']=str(self.bad/'Scripts')+';'+str(Path(os.environ['SystemRoot'])/'System32')

    def tearDown(self):
        self.temp.cleanup()

    def write_main(self,exit_code):
        (self.app/'main.py').write_text(
            'import customtkinter,sys,json\nfrom pathlib import Path\n'
            'Path(__file__).with_name("launched.json").write_text(json.dumps({"executable":sys.executable}))\n'
            'raise SystemExit('+str(exit_code)+')\n',encoding='utf-8')

    def clone_env(self,template,directory):
        shutil.copytree(template,directory)
        return directory/'Scripts/python.exe'

    def run_bat(self,name):
        return subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c','call',str(self.app/name)],
            cwd=self.repo,env=self.env,input=b'\r\n',capture_output=True,timeout=90)

    def launched(self):
        return Path(json.loads((self.app/'launched.json').read_text())['executable'])

    def test_project_venv_beats_incomplete_global_python(self):
        expected=self.clone_env(self.good,self.repo/'.venv')
        result=self.run_bat('INICIAR_MRS.bat')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.launched().resolve(),expected.resolve())

    def test_active_environment_has_priority(self):
        self.clone_env(self.good,self.repo/'.venv')
        self.env['VIRTUAL_ENV']=str(self.good)
        result=self.run_bat('INICIAR_MRS.bat')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.launched().resolve(),(self.good/'Scripts/python.exe').resolve())

    def test_explicit_python_can_reuse_an_existing_local_installation(self):
        self.env['MRS_PYTHON']=str(self.good/'Scripts/python.exe')
        result=self.run_bat('INICIAR_MRS.bat')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.launched().resolve(),(self.good/'Scripts/python.exe').resolve())

    def test_incomplete_active_environment_falls_back_to_ready_project(self):
        expected=self.clone_env(self.good,self.repo/'.venv')
        self.env['VIRTUAL_ENV']=str(self.bad)
        result=self.run_bat('INICIAR_MRS.bat')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.launched().resolve(),expected.resolve())

    def test_check_and_start_use_same_environment_without_launching_during_check(self):
        expected=self.clone_env(self.good,self.app/'.venv')
        result=self.run_bat('INSTALAR.bat')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse((self.app/'launched.json').exists())
        result=self.run_bat('INICIAR_MRS.bat')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.launched().resolve(),expected.resolve())

    def test_incomplete_runtime_is_not_reported_as_installed(self):
        target=self.repo/'runtime/python';target.mkdir(parents=True)
        shutil.copyfile(self.bad/'Scripts/python.exe',target/'python.exe')
        shutil.copyfile(self.bad/'pyvenv.cfg',target.parent/'pyvenv.cfg')
        result=self.run_bat('INSTALAR.bat')
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertFalse((self.app/'launched.json').exists())
        self.assertIn(b'customtkinter',result.stdout)

    def test_ready_runtime_is_used_before_incomplete_global_python(self):
        target=self.repo/'runtime/python';target.mkdir(parents=True)
        shutil.copyfile(self.good/'Scripts/python.exe',target/'python.exe')
        shutil.copyfile(self.good/'pyvenv.cfg',target.parent/'pyvenv.cfg')
        result=self.run_bat('INICIAR_MRS.bat')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.launched().resolve(),(target/'python.exe').resolve())

    def test_application_exit_code_is_preserved(self):
        self.clone_env(self.good,self.repo/'.venv')
        self.write_main(23)
        result=self.run_bat('INICIAR_MRS.bat')
        self.assertEqual(result.returncode,23,result.stdout+result.stderr)


if __name__=='__main__':
    unittest.main(verbosity=2)
