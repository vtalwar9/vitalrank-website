#!/usr/bin/env python3
"""Extract CMS defaults from annotated HTML templates.

Scans HTML files + build.py for <!-- cms:... --> markers and writes the
default values into the content files (content/pages/*.yml,
content/services/*.md frontmatter, content/settings/site.yml).

List markers get `key: []` — fill list data manually afterwards.
Outputs an inventory JSON for config generation.
"""
import re, html as htmlmod, json, os, sys

try:
    import yaml
except ImportError:
    print('pyyaml required')
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMS_RE = re.compile(
    r'<!--\s*cms:(s|t|m|mi|h|img|list|posts):([A-Za-z0-9_.:]+?)\s*-->(.*?)<!--\s*/cms\s*-->',
    re.S)


def html_to_md(html):
    h = html
    h = re.sub(r'<br\s*/?>', '\n', h)
    # lists
    def list_repl(m):
        tag, inner = m.group(1), m.group(2)
        items = re.findall(r'<li>(.*?)</li>', inner, re.S)
        out = []
        for i, it in enumerate(items):
            it = inline(it)
            out.append(('- ' if tag == 'ul' else '%d. ' % (i + 1)) + it.strip())
        return '\n'.join(out)
    h = re.sub(r'<(ul|ol)[^>]*>(.*?)</\1>', list_repl, h, flags=re.S)
    h = re.sub(r'<h2>(.*?)</h2>', lambda m: '## ' + inline(m.group(1)), h, flags=re.S)
    h = re.sub(r'<h3>(.*?)</h3>', lambda m: '### ' + inline(m.group(1)), h, flags=re.S)
    h = re.sub(r'<h4>(.*?)</h4>', lambda m: '#### ' + inline(m.group(1)), h, flags=re.S)
    h = re.sub(r'<p>(.*?)</p>', lambda m: inline(m.group(1)) + '\n', h, flags=re.S)
    h = re.sub(r'<[^>]+>', '', h)
    h = htmlmod.unescape(h)
    # collapse 3+ newlines, strip lines
    h = re.sub(r'\n{3,}', '\n\n', h)
    return h.strip()


def inline(s):
    s = re.sub(r'<strong>(.*?)</strong>', r'**\1**', s, flags=re.S)
    s = re.sub(r'<b>(.*?)</b>', r'**\1**', s, flags=re.S)
    s = re.sub(r'<em>(.*?)</em>', r'*\1*', s, flags=re.S)
    s = re.sub(r'<i>(.*?)</i>', r'*\1*', s, flags=re.S)
    s = re.sub(r'<code>(.*?)</code>', r'`\1`', s, flags=re.S)
    s = re.sub(r'<a href="([^"]+)">(.*?)</a>', r'[\2](\1)', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    return htmlmod.unescape(s).strip()


def target_for(key, page_map):
    """Return (content_path, field_name, is_site) for a marker key."""
    if key.startswith('site.'):
        return ('content/settings/site.yml', key[5:], True)
    return (None, key, False)  # page file resolved by caller


def main():
    # (html_path, content_path) — content_path None means build.py chrome
    scans = [
        ('index.html', 'content/pages/home.yml'),
        ('about-us/index.html', 'content/pages/about.yml'),
        ('services/index.html', 'content/pages/services.yml'),
        ('contact/index.html', 'content/pages/contact.yml'),
        ('blog/index.html', 'content/pages/blog.yml'),
        ('build.py', None),  # chrome templates (site.* keys)
    ]
    service_files = []
    import glob as g
    for md in sorted(g.glob(os.path.join(ROOT, 'content', 'services', '*.md'))):
        slug = os.path.splitext(os.path.basename(md))[0]
        scans.append(('services/%s/index.html' % slug, md))
        service_files.append(md)

    # load existing content
    store = {}
    def get_store(cpath):
        if cpath not in store:
            full = os.path.join(ROOT, cpath)
            if cpath.endswith('.md'):
                txt = open(full, encoding='utf-8').read()
                m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', txt, re.S)
                fm = yaml.safe_load(m.group(1)) if m else {}
                store[cpath] = {'__fm__': fm or {}, '__body__': m.group(2) if m else ''}
            else:
                store[cpath] = yaml.safe_load(open(full, encoding='utf-8').read()) or {}
        return store[cpath]

    inventory = {}  # key -> {kind, fields, pages}
    for html_rel, cpath in scans:
        html = open(os.path.join(ROOT, html_rel), encoding='utf-8').read()
        for m in CMS_RE.finditer(html):
            kind, keyspec, inner = m.group(1), m.group(2), m.group(3)
            key = keyspec.partition(':')[0]
            if key == 'testimonials' or kind == 'posts':
                inv_key = key
            else:
                inv_key = key
            inventory.setdefault(inv_key, {'kind': kind, 'fields': set(), 'pages': set()})
            inventory[inv_key]['pages'].add(html_rel)

            if kind == 'posts':
                continue
            if key == 'testimonials':
                continue
            # resolve content file
            if key.startswith('site.'):
                tcpath, field = 'content/settings/site.yml', key[5:]
            elif cpath is None:
                continue  # shouldn't happen (chrome keys are site.*)
            elif cpath.endswith('.md'):
                tcpath, field = cpath, key
            else:
                tcpath, field = cpath, key
            data = get_store(tcpath)
            target = data['__fm__'] if tcpath.endswith('.md') and '__fm__' in data else data

            if kind in ('s', 't'):
                val = htmlmod.unescape(inner).strip()
                val = re.sub(r'[ \t]+', ' ', val)
                if kind == 's':
                    val = re.sub(r'\s+', ' ', val)
                target[field] = val
            elif kind == 'h':
                target[field] = inner.strip()
            elif kind == 'mi':
                target[field] = inline(inner)
            elif kind == 'm':
                md = html_to_md(inner)
                if tcpath.endswith('.md') and field == 'body':
                    data['__body__'] = md + '\n'
                else:
                    target[field] = md
            elif kind == 'img':
                sm = re.search(r'src="([^"]+)"', inner)
                am = re.search(r'alt="([^"]*)"', inner)
                if sm:
                    target[field] = sm.group(1)
                if am:
                    target[field + '_alt'] = htmlmod.unescape(am.group(1))
            elif kind == 'list':
                tm = re.search(r'<template>(.*?)</template>', inner, re.S)
                tpl = tm.group(1) if tm else inner
                fields = re.findall(r'\{\{\{(\w+)\}\}\}', tpl) + re.findall(r'\{\{(\w+)\}\}', tpl)
                seen = set()
                for f in fields:
                    if f not in seen:
                        seen.add(f)
                        inventory[inv_key]['fields'].add(f)
                if field not in target or not isinstance(target.get(field), list):
                    target[field] = []

    # write back
    for cpath, data in store.items():
        full = os.path.join(ROOT, cpath)
        if cpath.endswith('.md'):
            fm, body = data['__fm__'], data['__body__']
            out = '---\n' + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + '---\n\n' + body
            # body may have been replaced via m:body marker? No — body marker reads __body__.
            open(full, 'w', encoding='utf-8').write(out)
            print('updated', cpath)
        else:
            open(full, 'w', encoding='utf-8').write(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
            print('updated', cpath)

    inv = {k: {'kind': v['kind'], 'fields': sorted(v['fields']),
               'pages': sorted(v['pages'])} for k, v in sorted(inventory.items())}
    json.dump(inv, open('/tmp/cms_inventory.json', 'w'), indent=1)
    print('inventory:', len(inv), 'markers -> /tmp/cms_inventory.json')
    for k, v in inv.items():
        if v['kind'] == 'list':
            print('  LIST', k, v['fields'])


if __name__ == '__main__':
    main()
