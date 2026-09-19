#!/usr/local/bin/python3
# Copyright (C) 2026 Abdelmonem Awad <eg2@live.com>. BSD 2-Clause License, see LICENSE.
"""
Right-to-left layout for the OPNsense GUI when the language is Arabic or Persian.

  apply_rtl.py            patch the page templates and build the mirrored stylesheets
  apply_rtl.py --remove   put the original templates back and delete the mirrored stylesheets

The first run keeps pristine copies of the templates in /root/opnsense-rtl/backup. Core
updates replace the templates, so this runs again at boot (rc.syshook.d/start/61-opnsense-rtl);
it only changes what is not patched yet.
"""
import glob
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP = '/root/opnsense-rtl/backup'
VOLT = '/usr/local/opnsense/mvc/app/views/layouts/default.volt'
HEAD = '/usr/local/www/head.inc'
AUTH = '/usr/local/www/authgui.inc'     # login and error pages
MARK = 'opnsense-rtl'

VOLT_PATCHES = [
    # direction on the root element
    ('<html lang="{{ langcode|safe }}" class="no-js">',
     "{# opnsense-rtl #}{% set rtl_ui = langcode|slice(0, 1) in ['ar', 'fa'] %}"
     '<html lang="{{ langcode|safe }}"{% if rtl_ui %} dir="rtl"{% endif %} class="no-js">'),
    # mirrored stylesheets (icon fonts stay as they are); note: volt slice() end index is inclusive
    ('<link href="{{ cache_safe(theme_file_or_default(filename, theme_name)) }}" rel="stylesheet">',
     '{% set css_path = theme_file_or_default(filename, theme_name) %}'
     "{% if rtl_ui and css_path|slice(0, 10) != '/ui/assets/' and css_path|slice(-4) == '.css' %}"
     "{% set css_path = css_path|slice(0, css_path|length - 5) ~ '.rtl.css' %}{% endif %}"
     '<link href="{{ cache_safe(css_path) }}" rel="stylesheet">'),
]

HEAD_FUNCS = '''
/* opnsense-rtl: right-to-left layout for Arabic and Persian */
if (!function_exists('rtl_ui')) {
    function rtl_ui()
    {
        return in_array(substr(get_current_lang(), 0, 2), ['ar', 'fa']);
    }
    function rtl_css($path)
    {
        if (!rtl_ui() || strpos($path, '/ui/assets/') === 0) {
            return $path;
        }
        $rtl = preg_replace('/\\.css$/', '.rtl.css', $path);
        return file_exists('/usr/local/opnsense/www' . preg_replace('#^/ui#', '', $rtl)) ? $rtl : $path;
    }
}

'''


def patch_volt():
    text = open(VOLT, encoding='utf-8').read()
    if MARK in text:
        return False
    for old, new in VOLT_PATCHES:
        if old not in text:
            raise RuntimeError(f'{VOLT}: expected markup not found, template changed upstream: {old[:60]}')
        text = text.replace(old, new)
    open(VOLT, 'w', encoding='utf-8').write(text)
    return True


HTML_TAG = '<html lang="<?= get_current_lang() ?>" class="no-js">'
HTML_RTL = '<html lang="<?= get_current_lang() ?>"<?= rtl_ui() ? \' dir="rtl"\' : \'\' ?> class="no-js">'


def patch_php(path, anchor, before):
    """add the helper functions at anchor, set the direction and route stylesheets through rtl_css()"""
    text = open(path, encoding='utf-8').read()
    if MARK in text:
        return False
    if anchor not in text or HTML_TAG not in text:
        raise RuntimeError(f'{path}: expected markup not found, template changed upstream')
    text = text.replace(anchor, HEAD_FUNCS + anchor if before else anchor + HEAD_FUNCS, 1)
    text = text.replace(HTML_TAG, HTML_RTL)
    text = re.sub(r"cache_safe\(get_themed_filename\(([^()]*\.css['\"])\)\)", r'cache_safe(rtl_css(get_themed_filename(\1)))', text)
    open(path, 'w', encoding='utf-8').write(text)
    return True


def patch_head():
    return patch_php(HEAD, '?><!doctype html>', True)


def patch_auth():
    return patch_php(AUTH, '<?php\n', False)


def lint(path):
    if path.endswith('.inc'):
        subprocess.run(['php', '-l', path], check=True, capture_output=True)
    else:
        # same custom filter as ControllerBase registers; unknown functions compile to macro calls
        code = ("require_once '/usr/local/opnsense/mvc/script/load_phalcon.php';"
                "$c = new Phalcon\\Mvc\\View\\Engine\\Volt\\Compiler(); $c->addFilter('safe', 'view_html_safe');"
                f"$c->compileString(file_get_contents('{path}'));")
        subprocess.run(['php', '-r', code], check=True, capture_output=True)


def clear_caches():
    for path in glob.glob('/usr/local/opnsense/mvc/app/cache/*.php'):
        os.unlink(path)
    subprocess.run('configctl webgui restart', shell=True, capture_output=True)


def apply():
    os.makedirs(BACKUP, exist_ok=True)
    changed = False
    for path, patch in ((VOLT, patch_volt), (HEAD, patch_head), (AUTH, patch_auth)):
        pristine = os.path.join(BACKUP, os.path.basename(path))
        if MARK not in open(path, encoding='utf-8').read():
            shutil.copy2(path, pristine)          # refresh the backup with the current (possibly updated) original
        if patch():
            try:
                lint(path)
            except subprocess.CalledProcessError:
                shutil.copy2(pristine, path)
                raise RuntimeError(f'{path}: patched template did not compile, original restored')
            changed = True
    subprocess.run([sys.executable, os.path.join(HERE, 'make_rtl_css.py')], check=True)
    if changed:
        clear_caches()
    print('right-to-left layout active for Arabic and Persian' + (' (templates patched)' if changed else ''))


def remove():
    for path in (VOLT, HEAD, AUTH):
        pristine = os.path.join(BACKUP, os.path.basename(path))
        if MARK in open(path, encoding='utf-8').read() and os.path.exists(pristine):
            shutil.copy2(pristine, path)
    for path in glob.glob('/usr/local/opnsense/www/css/*.rtl.css') + \
            glob.glob('/usr/local/opnsense/www/themes/*/build/css/*.rtl.css'):
        os.unlink(path)
    clear_caches()
    print('right-to-left layout removed')


if __name__ == '__main__':
    remove() if '--remove' in sys.argv else apply()
