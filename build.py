#!/usr/bin/env python3
"""Build the ViTalRank site: applies Decap CMS content to the static HTML
templates (marker regions), then renders the blog.

Usage:  python3 build.py
Content model:
  content/pages/*.yml        one file per main page (home, about, services, contact, blog)
  content/services/*.md      one file per service (YAML frontmatter fields + markdown body)
  content/settings/site.yml  shared header / CTA / footer content
  content/testimonials.yml   shared testimonials
  content/blog/*.md          blog posts

Marker syntax inside the HTML templates (markers are preserved in the output,
so builds are idempotent):
  <!-- cms:s:key -->...<!-- /cms -->    short string (HTML-escaped)
  <!-- cms:t:key -->...<!-- /cms -->    long text (HTML-escaped)
  <!-- cms:m:key -->...<!-- /cms -->    markdown block -> HTML
  <!-- cms:m:key:dots -->...<!-- /cms -->  markdown, <ul> gets class="dots"
  <!-- cms:img:key -->...<img ...>...<!-- /cms -->  image (fields: key, key_alt)
  <!-- cms:list:key -->
  <template>...{{field}} / {{{raw_html}}}...</template>
  <!-- /cms -->                         repeated block: the <template> is kept
                                        verbatim and items are re-rendered after it
  <!-- cms:posts:recent -->
  <template>...</template>
  <!-- /cms -->                         latest 3 blog posts, same mechanism

Key prefixes:  site.*       -> content/settings/site.yml
               testimonials -> content/testimonials.yml
               anything else -> the page's own content file
               (service markdown body is addressable as key "body")
"""
import re, glob, os, html as htmlmod
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

ROOT = os.path.dirname(os.path.abspath(__file__))

CHROME_HEADER = """
<header class="site-header">
  <div class="header-bar">
    <a class="logo" href="/" aria-label="ViTalRank — home"><!-- cms:img:site.logo --><img src="/assets/logo.svg" alt="ViTalRank" width="176" height="40"><!-- /cms --></a>
    <nav class="main-nav" aria-label="Main navigation">
      <a href="/"><!-- cms:s:site.nav_home -->Home<!-- /cms --></a>
      <a href="/about-us/"><!-- cms:s:site.nav_about -->About<!-- /cms --></a>
      <a href="/services/"><!-- cms:s:site.nav_services -->Services<!-- /cms --></a>
      <a href="/blog/"><!-- cms:s:site.nav_blog -->Blog<!-- /cms --></a>
    </nav>
    <a class="btn btn-outline-d" href="/contact/"><!-- cms:s:site.nav_contact -->Contact<!-- /cms --></a>
    <button class="nav-toggle" aria-label="Toggle menu"><span></span><span></span><span></span></button>
  </div>
</header>
"""

CHROME_CTA_FOOTER = """
<div class="band" style="padding-bottom:24px">
  <section class="cta-band">
    <h2 class="reveal"><!-- cms:s:site.cta_title -->Ready to transform your business?<!-- /cms --></h2>
    <a class="btn btn-outline-w reveal" href="/contact/"><!-- cms:s:site.cta_button -->Get started<!-- /cms --></a>
    <hr class="cta-divider">
    <footer class="site-footer">
      <div class="footer-grid">
        <div class="footer-brand">
          <!-- cms:img:site.logo_white --><img src="/assets/logo-white.svg" alt="ViTalRank" width="176" height="40"><!-- /cms -->
          <p><!-- cms:t:site.footer_text -->Industry-leading consulting firm with innovative solutions<!-- /cms --></p>
          <div class="social">
<!-- cms:list:site.social -->
<template>
<a href="{{url}}" aria-label="{{label}}">{{{icon}}}</a>
</template>
<!-- /cms -->
</div>
        </div>
        <div class="footer-col">
<h4><!-- cms:s:site.footer_col1_title -->Company<!-- /cms --></h4>
<!-- cms:list:site.footer_col1 -->
<template>
<a href="{{url}}">{{label}}</a>
</template>
<!-- /cms -->
</div>
        <div class="footer-col">
<h4><!-- cms:s:site.footer_col2_title -->Pages<!-- /cms --></h4>
<!-- cms:list:site.footer_col2 -->
<template>
<a href="{{url}}">{{label}}</a>
</template>
<!-- /cms -->
</div>
        <div class="footer-col">
<h4><!-- cms:s:site.footer_col3_title -->Services<!-- /cms --></h4>
<!-- cms:list:site.footer_col3 -->
<template>
<a href="{{url}}">{{label}}</a>
</template>
<!-- /cms -->
</div>
      </div>
      <div class="footer-bottom">
        <p><!-- cms:s:site.footer_copyright -->© 2026 ViTalRank. All rights reserved.<!-- /cms --></p>
        <div class="footer-contact">
<!-- cms:list:site.contact_info -->
<template>
<span class="fc-item"><span class="fc-label">{{label}}:</span> {{text}}</span>
</template>
<!-- /cms -->
        </div>
      </div>
    </footer>
  </section>
</div>
"""


def render_chrome(kind, sdata, posts):
    tpl = CHROME_HEADER if kind == "header" else CHROME_CTA_FOOTER
    return apply_markers(tpl, {}, sdata, posts)


def inject_chrome(html, sdata, posts):
    header_html = render_chrome("header", sdata, posts)
    footer_html = render_chrome("cta_footer", sdata, posts)
    if "<!-- chrome:header -->" in html:
        html = html.replace("<!-- chrome:header -->", header_html)
    elif '<header class="site-header">' in html:
        # chrome was injected by an earlier build: re-render in place so
        # template changes propagate on rebuild (markers stay idempotent)
        html = re.sub(r'<header class="site-header">.*?</header>',
                      lambda m: header_html, html, count=1, flags=re.S)
    if "<!-- chrome:cta_footer -->" in html:
        html = html.replace("<!-- chrome:cta_footer -->", footer_html)
    else:
        # re-render previously injected footer: find the footer band
        # just before the script tag and swap in the fresh template
        script_tag = '<script src="/script.js"></script>'
        si = html.find(script_tag)
        if si != -1:
            band_start = html.rfind('<div class="band" style="padding-bottom:24px">', 0, si)
            if band_start != -1 and 'site-footer' in html[band_start:si]:
                html = html[:band_start] + footer_html + html[si:]
    return html


# ----------------------------------------------------------------------------
# Template chunks (extracted verbatim from the original hand-built pages)
# ----------------------------------------------------------------------------
PRE_TITLE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
"""
MID_TEMPLATE = """
{META_DESC_TAG}
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
</head>
<body>

<!-- chrome:header -->

<section class="hero tall-dark" style="min-height:72svh">
  {HERO_IMG_TAG}
  <div class="hero-inner">
    <div class="container">
      <div class="hero-center">
        {DATE_PILL}
        {H1_TAG}
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="container">
    """
POST_ARTICLE = """
  </div>
</section>

<!-- chrome:cta_footer -->

<script src="/script.js"></script>
</body>
</html>
"""
INDEX_PRE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blog | ViTalRank | AI-Driven SEO &amp; Digital Services</title>
<meta name="description" content="Explore insights from the ViTalRank team — SEO best practices, strategy, and digital growth topics.">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
</head>
<body>

<!-- chrome:header -->

<section class="section" style="padding-top:150px">
  <div class="container center">
    <div class="label center reveal"><!-- cms:s:blog_label -->Blog posts<!-- /cms --></div>
    <h1 class="section-title reveal"><!-- cms:s:blog_title -->Our blog<!-- /cms --></h1>
    <h2 class="reveal" style="font-size:clamp(22px,2.6vw,30px);font-weight:600;margin-bottom:14px"><!-- cms:h:blog_subtitle -->Explore insights<br>and stay ahead<!-- /cms --></h2>
    <p class="lead reveal"><!-- cms:mi:blog_lead -->Our blog features insights from our team of consultants, who share their best practices on a wide range of topics.<!-- /cms --></p>
    <div class="blog-list" style="text-align:left">
"""
INDEX_POST = """</div>
  </div>
</section>

<!-- chrome:cta_footer -->

<script src="/script.js"></script>
</body>
</html>
"""
# ----------------------------------------------------------------------------
# Minimal Markdown -> HTML (headings, paragraphs, bold, italic, links,
# lists, blockquotes, inline code, hr). Dependency-free on purpose.
# ----------------------------------------------------------------------------
def inline_md(text):
    text = htmlmod.escape(text, quote=False)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^\*\n]+)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text

def md_to_html(md, ul_class=None):
    blocks, para, lst = [], [], None
    ul_attr = ' class="%s"' % ul_class if ul_class else ''
    def flush_para():
        if para:
            blocks.append('<p>' + ' '.join(para) + '</p>')
            para.clear()
    def flush_list():
        nonlocal lst
        if lst:
            tag = 'ol' if lst[0] == 'ol' else 'ul'
            attr = ul_attr if tag == 'ul' else ''
            blocks.append('<%s%s>' % (tag, attr) + ''.join('<li>%s</li>' % i for _, i in lst[1:]) + '</%s>' % tag)
            lst = None
    for raw in md.split('\n'):
        line = raw.strip()
        if not line:
            flush_para(); flush_list(); continue
        m = re.match(r'^(#{1,3})\s+(.*)$', line)
        if m:
            flush_para(); flush_list()
            blocks.append('<h%d>%s</h%d>' % (len(m.group(1)), inline_md(m.group(2)), len(m.group(1))))
            continue
        if re.match(r'^---+$', line):
            flush_para(); flush_list(); blocks.append('<hr>'); continue
        if line.startswith('> '):
            flush_para(); flush_list()
            blocks.append('<blockquote><p>%s</p></blockquote>' % inline_md(line[2:].strip()))
            continue
        m = re.match(r'^([-*])\s+(.*)$', line)
        if m:
            flush_para()
            if not lst or lst[0] != 'ul': flush_list(); lst = ['ul']
            lst.append(('ul', inline_md(m.group(2)))); continue
        m = re.match(r'^(\d+)\.\s+(.*)$', line)
        if m:
            flush_para()
            if not lst or lst[0] != 'ol': flush_list(); lst = ['ol']
            lst.append(('ol', inline_md(m.group(2)))); continue
        if lst: flush_list()
        para.append(inline_md(line))
    flush_para(); flush_list()
    return '\n'.join(blocks)

# ----------------------------------------------------------------------------
# CMS marker engine
# ----------------------------------------------------------------------------
CMS_RE = re.compile(
    r'<!--\s*cms:(s|t|m|mi|h|img|list|posts):([A-Za-z0-9_.:]+?)\s*-->(.*?)<!--\s*/cms\s*-->',
    re.S)
TPL_RE = re.compile(r'<template>(.*?)</template>', re.S)


def load_yaml_file(path):
    if not yaml or not os.path.exists(path):
        return {}
    try:
        return yaml.safe_load(open(path, encoding='utf-8').read()) or {}
    except Exception as e:
        print('YAML parse failed for %s: %s' % (path, e))
        return {}


def load_service_md(path):
    """Return (frontmatter dict, body markdown) for a service file."""
    txt = open(path, encoding='utf-8').read()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', txt, re.S)
    if not m:
        return {}, txt
    fm = yaml.safe_load(m.group(1)) if yaml else {}
    return (fm or {}), m.group(2)


def site_data():
    return load_yaml_file(os.path.join(ROOT, 'content', 'settings', 'site.yml'))


def testimonials_data():
    d = load_yaml_file(os.path.join(ROOT, 'content', 'testimonials.yml'))
    if isinstance(d, dict):
        return d.get('testimonials') or []
    return []


def cms_get(key, page_data, sdata):
    if key.startswith('site.'):
        return sdata.get(key[5:])
    if key == 'testimonials':
        return testimonials_data()
    if key in page_data:
        return page_data[key]
    if key == 'body' and '__body__' in page_data:
        return page_data['__body__']
    return None


def render_items(template, items):
    out = []
    for it in items:
        if not isinstance(it, dict):
            it = {'text': it}
        t = template
        t = re.sub(r'\{\{\{(\w+)\}\}\}',
                   lambda m: str(it.get(m.group(1), '')), t)
        t = re.sub(r'="\{\{(\w+)\}\}"',
                   lambda m: '="' + htmlmod.escape(str(it.get(m.group(1), '')), quote=True) + '"', t)
        t = re.sub(r"='\{\{(\w+)\}\}'",
                   lambda m: "='" + htmlmod.escape(str(it.get(m.group(1), '')), quote=True) + "'", t)
        t = re.sub(r'\{\{(\w+)\}\}',
                   lambda m: htmlmod.escape(str(it.get(m.group(1), '')), quote=False), t)
        # a link left with no URL becomes plain text (avoids dead href="")
        t = re.sub(r'<a href="">(.*?)</a>', r'<span>\1</span>', t)
        out.append(t.strip())
    return '\n'.join(out)


def set_img_attrs(tag, src, alt):
    tag = re.sub(r'src="[^"]*"',
                 'src="%s"' % htmlmod.escape(src, quote=True), tag, count=1)
    if alt is None:
        return tag
    alt_esc = htmlmod.escape(str(alt), quote=True)
    if re.search(r'\balt="', tag):
        tag = re.sub(r'alt="[^"]*"', 'alt="%s"' % alt_esc, tag, count=1)
    else:
        tag = tag.replace('<img', '<img alt="%s"' % alt_esc, 1)
    return tag


def apply_markers(html, page_data, sdata, posts):
    """Replace all cms marker regions with content values. Markers are kept
    in the output so the build stays idempotent."""
    def rep(m):
        kind, keyspec, inner = m.group(1), m.group(2), m.group(3)
        if ':' in keyspec:
            key, _, opt = keyspec.partition(':')
        else:
            key, opt = keyspec, ''
        open_c = '<!-- cms:%s:%s -->' % (kind, keyspec)
        close_c = '<!-- /cms -->'

        def list_render(items):
            tm = TPL_RE.search(inner)
            if not tm:
                return None
            template = tm.group(1)
            head = inner[:tm.end()]
            if not isinstance(items, list) or not items:
                return open_c + head + close_c
            return open_c + head + render_items(template, items) + close_c

        if kind == 'posts':
            items = []
            for fm in (posts or [])[:3]:
                items.append({
                    'url': '/blog/%s/' % fm['slug'],
                    'image': fm.get('image', ''),
                    'image_alt': fm.get('image_alt', fm.get('title', '')),
                    'date': display_date(fm['date_obj']),
                    'title': fm.get('title', ''),
                })
            rendered = list_render(items)
            return rendered if rendered is not None else m.group(0)

        val = cms_get(key, page_data, sdata)

        if kind == 'list':
            rendered = list_render(val)
            return rendered if rendered is not None else m.group(0)

        if val is None:
            return m.group(0)
        if kind in ('s', 't'):
            new_inner = htmlmod.escape(str(val).strip(), quote=False)
        elif kind == 'mi':
            new_inner = inline_md(str(val).strip())
        elif kind == 'h':
            new_inner = str(val).strip()
        elif kind == 'm':
            new_inner = md_to_html(str(val),
                                   ul_class=opt if opt else None)
        elif kind == 'img':
            src = str(val).strip()
            alt = cms_get(key + '_alt', page_data, sdata)
            new_inner = re.sub(r'<img\b[^>]*>',
                               lambda im: set_img_attrs(im.group(0), src, alt),
                               inner, count=1)
            mobile_src = cms_get(key + '_mobile', page_data, sdata)
            if mobile_src and '<source' in new_inner:
                ms = htmlmod.escape(str(mobile_src).strip(), quote=True)
                new_inner = re.sub(r'(<source\b[^>]*?\bsrcset=")[^"]*(")',
                                   r'\g<1>' + ms + r'\g<2>',
                                   new_inner, count=1)
            if new_inner == inner and src:
                # no <img> found in region; nothing to do
                return m.group(0)
        else:
            return m.group(0)
        return open_c + new_inner + close_c

    return CMS_RE.sub(rep, html)


def apply_meta(html, data):
    """Apply SEO title / meta description / OG tags from a content dict."""
    if not data:
        return html
    if data.get('seo_title'):
        html = re.sub(r'<title>.*?</title>',
                      '<title>' + htmlmod.escape(str(data['seo_title'])) + '</title>',
                      html, count=1, flags=re.S)
    if data.get('meta_description'):
        desc_esc = htmlmod.escape(str(data['meta_description']), quote=True)
        html = re.sub(r'<meta name="description" content=".*?">',
                      '<meta name="description" content="%s">' % desc_esc,
                      html, count=1)
    if data.get('og_title'):
        ogt_esc = htmlmod.escape(str(data['og_title']), quote=True)
        if 'property="og:title"' in html:
            html = re.sub(r'<meta property="og:title" content=".*?">',
                          '<meta property="og:title" content="%s">' % ogt_esc,
                          html, count=1)
    if data.get('og_description'):
        ogd_esc = htmlmod.escape(str(data['og_description']), quote=True)
        if 'property="og:description"' in html:
            html = re.sub(r'<meta property="og:description" content=".*?">',
                          '<meta property="og:description" content="%s">' % ogd_esc,
                          html, count=1)
    return html


# ----------------------------------------------------------------------------
# Frontmatter
# ----------------------------------------------------------------------------
def parse_post(path):
    txt = open(path, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n\n(.*)$', txt, re.S)
    if not m:
        raise ValueError('bad frontmatter: ' + path)
    fm = {}
    for line in m.group(1).split('\n'):
        k, v = line.split(':', 1)
        v = v.strip()
        if v.startswith('"') and v.endswith('"'): v = v[1:-1]
        fm[k.strip()] = v
    fm['body_md'] = m.group(2)
    fm['slug'] = fm.get('slug') or os.path.splitext(os.path.basename(path))[0]
    fm['date_obj'] = datetime.strptime(fm['date'], '%Y-%m-%d').date()
    return fm

def display_date(d):
    return d.strftime('%b ') + str(d.day) + d.strftime(', %Y')

# ----------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------
def render_post(fm):
    body_html = md_to_html(fm['body_md'])
    body_indented = '\n'.join(('      ' + ln) if ln.strip() else ln for ln in body_html.split('\n'))
    meta = '<meta name="description" content="%s">' % htmlmod.escape(fm['description'], quote=True)
    hero = '<img class="hero-bg" src="%s" alt="%s">' % (
        htmlmod.escape(fm['image'], quote=True), htmlmod.escape(fm.get('image_alt', ''), quote=True))
    out = PRE_TITLE + '<title>' + htmlmod.escape(fm['title']) + ' | ViTalRank</title>'
    mid = MID_TEMPLATE
    mid = mid.replace('{META_DESC_TAG}', meta)
    mid = mid.replace('{HERO_IMG_TAG}', hero)
    mid = mid.replace('{DATE_PILL}', '<span class="date-pill-hero">' + display_date(fm['date_obj']) + '</span>')
    mid = mid.replace('{H1_TAG}', '<h1>' + htmlmod.escape(fm['title']) + '</h1>')
    out += mid + '<article class="article-single">\n' + body_indented + '\n    </article>' + POST_ARTICLE
    return out

def render_index(posts):
    cards = []
    for fm in posts:
        cards.append(
            '      <a class="blog-card reveal" href="/blog/%s/">\n'
            '        <img src="%s" alt="%s">\n'
            '        <span class="date-pill">%s</span>\n'
            '        <span class="card-title">%s</span>\n'
            '      </a>' % (
                fm['slug'],
                htmlmod.escape(fm['image'], quote=True),
                htmlmod.escape(fm.get('card_alt', fm.get('image_alt', '')), quote=True),
                display_date(fm['date_obj']),
                htmlmod.escape(fm['title'])))
    return INDEX_PRE + '\n'.join(cards) + '\n    ' + INDEX_POST

PAGE_MAP = {
    'index.html': 'content/pages/home.yml',
    'about-us/index.html': 'content/pages/about.yml',
    'services/index.html': 'content/pages/services.yml',
    'contact/index.html': 'content/pages/contact.yml',
}

def build_page(rel, content_path, sdata, posts):
    html_path = os.path.join(ROOT, rel)
    if not os.path.exists(html_path):
        return
    page_data = load_yaml_file(os.path.join(ROOT, content_path))
    html = open(html_path, encoding='utf-8').read()
    html = inject_chrome(html, sdata, posts)
    html = apply_markers(html, page_data, sdata, posts)
    html = apply_meta(html, page_data)
    open(html_path, 'w', encoding='utf-8').write(html)
    print('built %s' % rel)

def build_service(md_path, sdata, posts):
    fm, body = load_service_md(md_path)
    slug = os.path.splitext(os.path.basename(md_path))[0]
    html_path = os.path.join(ROOT, 'services', slug, 'index.html')
    if not os.path.exists(html_path):
        return
    page_data = dict(fm)
    page_data['__body__'] = body
    html = open(html_path, encoding='utf-8').read()
    html = inject_chrome(html, sdata, posts)
    html = apply_markers(html, page_data, sdata, posts)
    html = apply_meta(html, fm)
    open(html_path, 'w', encoding='utf-8').write(html)
    print('built services/%s/' % slug)

def main():
    if not yaml:
        print('pyyaml not available; CMS content cannot be applied')
        return
    sdata = site_data()
    posts = [parse_post(p) for p in glob.glob(os.path.join(ROOT, 'content', 'blog', '*.md'))]
    posts.sort(key=lambda f: (f['date_obj'], f['slug']), reverse=False)
    posts.sort(key=lambda f: f['date_obj'], reverse=True)  # stable: date desc, slug asc on ties

    for rel, content_path in PAGE_MAP.items():
        build_page(rel, content_path, sdata, posts)

    for md_path in glob.glob(os.path.join(ROOT, 'content', 'services', '*.md')):
        build_service(md_path, sdata, posts)

    for fm in posts:
        d = os.path.join(ROOT, 'blog', fm['slug'])
        os.makedirs(d, exist_ok=True)
        html = apply_markers(inject_chrome(render_post(fm), sdata, posts), dict(fm), sdata, posts)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(html)
        print('wrote blog/%s/index.html' % fm['slug'])

    blog_data = load_yaml_file(os.path.join(ROOT, 'content', 'pages', 'blog.yml'))
    html = apply_markers(inject_chrome(render_index(posts), sdata, posts), blog_data, sdata, posts)
    html = apply_meta(html, blog_data)
    open(os.path.join(ROOT, 'blog', 'index.html'), 'w', encoding='utf-8').write(html)
    print('wrote blog/index.html (%d posts)' % len(posts))

if __name__ == '__main__':
    main()
