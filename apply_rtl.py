#!/usr/local/bin/python3
# Copyright (C) 2026 Abdelmonem Awad <eg2@live.com>. BSD 2-Clause License, see LICENSE.
"""
Right-to-left layout for the OPNsense GUI when the language is Arabic or Persian.

  apply_rtl.py                patch the page templates and build the mirrored stylesheets
  apply_rtl.py --no-restart   the same, without restarting the web GUI (the pkg trigger)
  apply_rtl.py --remove       put the original templates back and delete the mirrored stylesheets

The first run keeps pristine copies of the templates in /root/opnsense-rtl/backup. Core
updates replace the templates, so this runs again when pkg writes one of them
(/usr/local/share/pkg/triggers/opnsense-rtl.ucl) and at every boot
(rc.syshook.d/start/61-opnsense-rtl); it only changes what is not patched yet.
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
# Raised whenever VOLT_PATCHES change, so a template patched by an older version is patched again,
# from the original kept in BACKUP, instead of being left as it was because it carries MARK.
VOLT_MARK = 'opnsense-rtl 2'

# A table OPNsense builds (UIBootgrid on Tabulator) keeps its columns in this browser's
# localStorage, under tabulator-<page>#<table>-columns, their titles included, and puts them back
# over the titles the page was rendered with. Once the interface language changes, every table
# a browser had shown before would keep its old titles (opnsense-arabic#9). This forgets the
# titles - and only the titles: widths, order and the columns shown stay - whenever the page's
# language is not the one they were kept under. It runs in <head>, before any table is built, in
# every language, not only in a right-to-left one.
TITLES_SCRIPT = (
    '{# opnsense-rtl: forget the column titles kept in another language #}'
    '<script>(function () { try {'
    " var lang = document.documentElement.lang || '', seen = 'opnsense-rtl-columns-lang';"
    ' if (localStorage.getItem(seen) === lang) { return; }'
    ' for (var i = 0; i < localStorage.length; i++) {'
    ' var key = localStorage.key(i);'
    " if (!key || key.indexOf('tabulator-') !== 0 || !/-columns$/.test(key)) { continue; }"
    ' var columns = JSON.parse(localStorage.getItem(key));'
    ' if (!Array.isArray(columns)) { continue; }'
    ' (function strip(list) { list.forEach(function (c) { if (c && typeof c === "object") {'
    ' delete c.title; if (Array.isArray(c.columns)) { strip(c.columns); } } }); })(columns);'
    ' localStorage.setItem(key, JSON.stringify(columns));'
    ' }'
    ' localStorage.setItem(seen, lang);'
    ' } catch (e) {} })();</script>'
)

VOLT_PATCHES = [
    # direction on the root element
    ('<html lang="{{ langcode|safe }}" class="no-js">',
     "{# opnsense-rtl 2 #}{% set rtl_ui = langcode|slice(0, 1) in ['ar', 'fa'] %}"
     '<html lang="{{ langcode|safe }}"{% if rtl_ui %} dir="rtl"{% endif %} class="no-js">'),
    # mirrored stylesheets (icon fonts stay as they are); note: volt slice() end index is inclusive
    ('<link href="{{ cache_safe(theme_file_or_default(filename, theme_name)) }}" rel="stylesheet">',
     '{% set css_path = theme_file_or_default(filename, theme_name) %}'
     "{% if rtl_ui and css_path|slice(0, 10) != '/ui/assets/' and css_path|slice(-4) == '.css' %}"
     "{% set css_path = css_path|slice(0, css_path|length - 5) ~ '.rtl.css' %}{% endif %}"
     '<link href="{{ cache_safe(css_path) }}" rel="stylesheet">'),
    # the column titles a browser kept in another language
    ('<meta charset="UTF-8" />', '<meta charset="UTF-8" />' + TITLES_SCRIPT),
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
    if VOLT_MARK in text:
        return False
    if MARK in text:
        # patched by an older version: start again from the original
        pristine = os.path.join(BACKUP, os.path.basename(VOLT))
        if not os.path.exists(pristine):
            raise RuntimeError(f'{VOLT}: patched by an older version and no original kept in {BACKUP}')
        text = open(pristine, encoding='utf-8').read()
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


def clear_caches(restart=True):
    for path in glob.glob('/usr/local/opnsense/mvc/app/cache/*.php'):
        os.unlink(path)
    if restart:
        subprocess.run('configctl webgui restart', shell=True, capture_output=True)


def apply(restart=True):
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
        clear_caches(restart)
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
    remove() if '--remove' in sys.argv else apply(restart='--no-restart' not in sys.argv)
