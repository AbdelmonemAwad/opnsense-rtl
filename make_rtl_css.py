#!/usr/local/bin/python3
# Copyright (C) 2026 Abdelmonem Awad <eg2@live.com>. BSD 2-Clause License, see LICENSE.
"""
Build right-to-left copies of the OPNsense stylesheets: every X.css gets an X.rtl.css next to it
with the horizontal geometry mirrored (left <-> right in properties and values, 4-value box
shorthands, border radii, horizontal translations). The GUI templates load the .rtl.css copies
when the interface language is written right to left (Arabic, Persian).

  make_rtl_css.py [file.css ...]      default: all stylesheets of the GUI and its themes
"""
import glob
import os
import re
import sys

ROOTS = ['/usr/local/opnsense/www/css', '/usr/local/opnsense/www/themes/*/build/css']
EXTRA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rtl-extra.css')

SWAP = re.compile(r'\b(left|right)\b')
BOX4 = {'margin', 'padding', 'border-width', 'border-color', 'border-style', 'inset',
        'scroll-margin', 'scroll-padding'}
KEYWORD_PROPS = {'float', 'clear', 'text-align', 'text-align-last', 'caption-side', 'justify-content',
                 'transition', 'transition-property', 'will-change', 'background-position',
                 'background-position-x', 'background', 'object-position', 'transform-origin',
                 'perspective-origin', 'mask-position'}
CURSORS = {'e-resize': 'w-resize', 'w-resize': 'e-resize', 'ne-resize': 'nw-resize', 'nw-resize': 'ne-resize',
           'se-resize': 'sw-resize', 'sw-resize': 'se-resize'}
RULE_BLOCKS = ('@media', '@supports', '@document', '@layer', '@container')


def swap_words(text):
    return SWAP.sub(lambda m: 'right' if m.group(1) == 'left' else 'left', text)


def split_top(text, sep):
    """split on sep outside parentheses and quotes"""
    parts, depth, quote, cur = [], 0, None, ''
    for ch in text:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in '"\'':
            quote = ch
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    return parts


def negate(v):
    v = v.strip()
    if re.match(r'^-?0(\.0+)?[a-z%]*$', v):
        return v
    if v.startswith('-'):
        return v[1:]
    if v.startswith('calc('):
        return f'calc(-1 * {v[5:-1]})'
    return '-' + v


def flip_transform(value):
    def tx(m):
        return f'{m.group(1)}({negate(m.group(2))})'

    def t2(m):
        args = split_top(m.group(2), ',')
        args[0] = negate(args[0])
        return f'{m.group(1)}({", ".join(a.strip() for a in args)})'
    value = re.sub(r'(translateX)\(([^()]*(?:\([^()]*\))?[^()]*)\)', tx, value)
    value = re.sub(r'(translate3d|translate)\(([^()]*(?:\([^()]*\))?[^()]*)\)', t2, value)
    return value


def flip_decl(decl):
    if ':' not in decl:
        return decl
    prop, value = decl.split(':', 1)
    name = prop.strip().lower()
    bare = re.sub(r'^-(webkit|moz|ms|o)-', '', name)
    important = ''
    m = re.search(r'\s*!important\s*$', value, re.I)
    if m:
        important, value = value[m.start():], value[:m.start()]

    # property names: margin-left -> margin-right, border-top-left-radius -> border-top-right-radius
    if re.search(r'(^|-)(left|right)(-|$)', bare):
        prop = swap_words(prop)
    elif bare in BOX4:
        vals = value.split()
        if len(vals) == 4 and 'url(' not in value:
            vals[1], vals[3] = vals[3], vals[1]
            lead = value[:len(value) - len(value.lstrip())]
            value = lead + ' '.join(vals)
    elif bare == 'border-radius':
        out = []
        for part in value.split('/'):
            v = part.split()
            if len(v) == 4:
                v = [v[1], v[0], v[3], v[2]]
            elif len(v) == 3:
                v = [v[1], v[0], v[1], v[2]]
            elif len(v) == 2:
                v = [v[1], v[0]]
            out.append(' '.join(v))
        value = ' ' + ' / '.join(out)
    elif bare in KEYWORD_PROPS and 'url(' not in value:
        value = swap_words(value)
        if bare in ('background-position', 'background-position-x'):
            value = re.sub(r'^(\s*)(\d+(?:\.\d+)?)%', lambda mm: f'{mm.group(1)}{100 - float(mm.group(2)):g}%', value)
    elif bare == 'transform':
        value = flip_transform(value)
    elif bare == 'cursor':
        value = re.sub(r'\b(e|w|ne|nw|se|sw)-resize\b', lambda mm: CURSORS[mm.group(0)], value)
    elif bare == 'direction':
        value = value.replace('ltr', '__tmp__').replace('rtl', 'ltr').replace('__tmp__', 'rtl')
    return prop + ':' + value + important


def flip_block(body):
    return ';'.join(flip_decl(d) if d.strip() else d for d in split_top(body, ';'))


def flip_css(css):
    out, i, n = [], 0, len(css)
    stack = []            # block kinds: 'rules' or 'decls'
    prelude_start = 0
    while i < n:
        if css.startswith('/*', i):
            j = css.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(css[i:j])
            i = j
            continue
        ch = css[i]
        if ch == '{':
            prelude = css[prelude_start:i].strip()
            kind = 'rules' if prelude.lower().startswith(RULE_BLOCKS) else 'decls'
            out.append(ch)
            i += 1
            if kind == 'decls':
                # find the matching close brace, declaration blocks do not nest
                depth, j, quote = 0, i, None
                while j < n:
                    c = css[j]
                    if quote:
                        if c == quote:
                            quote = None
                    elif c in '"\'':
                        quote = c
                    elif c == '(':
                        depth += 1
                    elif c == ')':
                        depth -= 1
                    elif c == '}' and depth <= 0:
                        break
                    j += 1
                body = re.sub(r'/\*.*?\*/', '', css[i:j], flags=re.S)
                out.append(flip_block(body))
                out.append('}')
                i = j + 1
            else:
                stack.append(kind)
            prelude_start = i
            continue
        if ch == '}':
            if stack:
                stack.pop()
            out.append(ch)
            i += 1
            prelude_start = i
            continue
        if ch == ';' and not stack:
            # top level statement such as @import or @charset
            out.append(ch)
            i += 1
            prelude_start = i
            continue
        if ch == ';':
            out.append(ch)
            i += 1
            prelude_start = i
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def targets():
    for root in ROOTS:
        for path in sorted(glob.glob(os.path.join(root, '*.css'))):
            if not path.endswith('.rtl.css'):
                yield path


def main():
    extra = open(EXTRA, encoding='utf-8').read() if os.path.exists(EXTRA) else ''
    files = sys.argv[1:] or list(targets())
    for path in files:
        css = open(path, encoding='utf-8', errors='surrogateescape').read()
        rtl = flip_css(css)
        if os.path.basename(path) == 'main.css' and extra:
            rtl += '\n/* opnsense-rtl: manual adjustments */\n' + extra
        dest = path[:-4] + '.rtl.css'
        with open(dest, 'w', encoding='utf-8', errors='surrogateescape') as fh:
            fh.write(rtl)
        os.chmod(dest, 0o644)
    print(f'{len(files)} stylesheets mirrored')


if __name__ == '__main__':
    main()
