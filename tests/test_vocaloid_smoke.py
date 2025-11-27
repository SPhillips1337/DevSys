import os

def test_vocaloid_app_present():
    assert os.path.isdir('apps/vocaloid'), 'apps/vocaloid missing'

def test_php_has_ffmpeg_installed():
    content = open('Dockerfile.php').read()
    assert 'ffmpeg' in content, 'ffmpeg not installed in Dockerfile.php'
