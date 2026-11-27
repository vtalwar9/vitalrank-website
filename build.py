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
  <!-- cms:a:key:attr -->...whole element...<!-- /cms -->  one attribute (attr="value")
  of the wrapped element is rewritten from the CMS value; the comments must
  stay OUTSIDE the tag or browsers leak the markup as visible text;
                                        the marker sits OUTSIDE the attribute so
                                        placeholders etc. render clean text
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
import re, glob, os, html as htmlmod, json
from datetime import datetime, date

try:
    import yaml
except ImportError:
    yaml = None

ROOT = os.path.dirname(os.path.abspath(__file__))

CHROME_HEADER = """
<header class="site-header">
  <div class="header-bar">
    <a class="logo" href="/" aria-label="ViTalRank — home"><!-- cms:img:site.logo --><img src="/assets/logo.svg" alt="ViTalRank" width="740" height="99"><!-- /cms --></a>
    <nav class="main-nav" aria-label="Main navigation">
      <a href="/"><!-- cms:s:site.nav_home -->Home<!-- /cms --></a>
      <a href="/about-us/"><!-- cms:s:site.nav_about -->About<!-- /cms --></a>
      <a href="/services/"><!-- cms:s:site.nav_services -->Services<!-- /cms --></a>
      <a href="/blog/"><!-- cms:s:site.nav_blog -->Blog<!-- /cms --></a>
      <a href="/contact/" class="nav-contact-link"><!-- cms:s:site.nav_contact -->Contact<!-- /cms --></a>
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
          <!-- cms:img:site.logo_white --><img src="/assets/logo-white.svg" alt="ViTalRank" width="740" height="99"><!-- /cms -->
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
        # template changes propagate on rebuild (markers stay idempotent).
        # Surrounding blank lines are swallowed so rebuilds don't
        # accumulate whitespace.
        html = re.sub(r'\n*<header class="site-header">.*?</header>\n*',
                      lambda m: '\n' + header_html.strip('\n') + '\n',
                      html, count=1, flags=re.S)
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
                # swallow preceding blank lines so rebuilds stay byte-stable
                bs = band_start
                while bs > 0 and html[bs - 1] == '\n':
                    bs -= 1
                html = html[:bs] + '\n' + footer_html.strip('\n') + '\n' + html[si:]
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
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
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
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
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
    r'<!--\s*cms:(s|t|m|mi|h|img|list|posts|a):([A-Za-z0-9_.:]+?)\s*-->(.*?)<!--\s*/cms\s*-->',
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

        if kind == 'a':
            # element-attribute marker: the comments wrap the WHOLE element,
            # e.g. <!-- cms:a:form_name_ph:placeholder --><input ... placeholder="Your name" ...><!-- /cms -->
            # Comments must never sit inside a tag: browsers end the tag at
            # the first ">" inside the comment and leak the rest as visible
            # text. Here we rewrite the named attribute's value in place.
            if val is None:
                return m.group(0)
            new_inner = re.sub(
                r'(%s\s*=\s*")([^"]*)(")' % re.escape(opt),
                lambda am: am.group(1) + htmlmod.escape(str(val).strip(), quote=True) + am.group(3),
                inner, count=1)
            return open_c + new_inner + close_c

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


def apply_head_tags(html, path, data, og_image=None, og_type='website'):
    """Insert canonical + complete Open Graph / Twitter share tags.

    Any existing canonical/og:/twitter: tags are stripped first, so the
    block is complete and idempotent across rebuilds.
    """
    data = data or {}
    html = re.sub(r'<link rel="canonical"[^>]*>\n?', '', html)
    html = re.sub(r'<meta property="og:[^>]*>\n?', '', html)
    html = re.sub(r'<meta name="twitter:[^>]*>\n?', '', html)
    title = data.get('og_title') or data.get('seo_title') or data.get('title') or 'ViTalRank'
    desc = (data.get('og_description') or data.get('meta_description')
            or data.get('description') or '')
    lines = ['<link rel="canonical" href="%s%s">' % (SITE_URL, path),
             '<meta property="og:title" content="%s">'
             % htmlmod.escape(str(title), quote=True)]
    if desc:
        lines.append('<meta property="og:description" content="%s">'
                     % htmlmod.escape(str(desc), quote=True))
    lines.append('<meta property="og:type" content="%s">' % og_type)
    lines.append('<meta property="og:url" content="%s%s">' % (SITE_URL, path))
    if og_image:
        img_abs = og_image if og_image.startswith('http') else SITE_URL + og_image
        lines.append('<meta property="og:image" content="%s">'
                     % htmlmod.escape(img_abs, quote=True))
    lines.append('<meta name="twitter:card" content="summary_large_image">')
    lines.append('<meta name="twitter:title" content="%s">'
                 % htmlmod.escape(str(title), quote=True))
    if desc:
        lines.append('<meta name="twitter:description" content="%s">'
                     % htmlmod.escape(str(desc), quote=True))
    if og_image:
        lines.append('<meta name="twitter:image" content="%s">'
                     % htmlmod.escape(img_abs, quote=True))
    block = '\n'.join(lines) + '\n'
    return html.replace('</head>', block + '</head>', 1)


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
# Structured data (JSON-LD schema) — generated from CMS content on every build,
# so edits to titles, descriptions, services, posts, contact info, or social
# links flow into the schema automatically. Replaces any existing block so
# rebuilds never duplicate it.
# ----------------------------------------------------------------------------

# Placeholder social URLs from the template — never ship these as sameAs.
_SOCIAL_PLACEHOLDERS = (
    'facebook.com/facebook', 'instagram.com/instagram',
    'youtube.com/youtube',
)

def _abs_url(path):
    if not path:
        return None
    return path if path.startswith('http') else SITE_URL + path

def _org_node(sdata):
    org_id = SITE_URL + '/#organization'
    org = {
        '@type': 'Organization',
        '@id': org_id,
        'name': sdata.get('site_name') or 'ViTalRank',
        'url': SITE_URL + '/',
    }
    if sdata.get('tagline'):
        org['description'] = sdata['tagline']
    logo = _abs_url(sdata.get('logo'))
    if logo:
        org['logo'] = logo
    same_as = [s.get('url') for s in (sdata.get('social') or [])
               if s.get('url') and not any(p in s['url'] for p in _SOCIAL_PLACEHOLDERS)
               and s['url'].rstrip('/') not in ('https://twitter.com', 'http://twitter.com')]
    if same_as:
        org['sameAs'] = same_as
    contact = {}
    for item in (sdata.get('contact_info') or []):
        label = str(item.get('label', '')).lower()
        href = str(item.get('href', '') or '')
        text = str(item.get('text', '') or '')
        if 'mail' in label and href.startswith('mailto:'):
            contact['email'] = href[len('mailto:'):]
        elif 'phone' in label or 'tel' in label:
            contact['telephone'] = text or href.replace('tel:', '')
    if contact:
        contact['@type'] = 'ContactPoint'
        contact['contactType'] = 'customer service'
        org['contactPoint'] = contact
    return org

def _service_list():
    """All services with built pages: (slug, title, description, image)."""
    out = []
    for md_path in sorted(glob.glob(os.path.join(ROOT, 'content', 'services', '*.md'))):
        slug = os.path.splitext(os.path.basename(md_path))[0]
        if not os.path.exists(os.path.join(ROOT, 'services', slug, 'index.html')):
            continue
        fm, _ = load_service_md(md_path)
        out.append((slug, fm.get('title', slug),
                    fm.get('meta_description', ''), fm.get('image')))
    return out

def build_jsonld(kind, page_data, sdata, extra=None):
    extra = extra or {}
    org = _org_node(sdata)
    org_id = org['@id']
    path = extra.get('path', '/')
    page_url = SITE_URL + path
    nodes = [org]
    if kind == 'home':
        nodes.append({
            '@type': 'WebSite', '@id': SITE_URL + '/#website',
            'url': SITE_URL + '/', 'name': org['name'],
            'publisher': {'@id': org_id},
        })
    webpage = {
        '@type': {
            'home': 'WebPage', 'about': 'AboutPage', 'services': 'CollectionPage',
            'service': 'WebPage', 'contact': 'ContactPage',
            'blog': 'Blog', 'post': 'BlogPosting',
        }[kind],
        '@id': page_url + '#webpage',
        'url': page_url,
        'name': page_data.get('seo_title') or page_data.get('title') or org['name'],
        'isPartOf': {'@id': SITE_URL + '/#website'} if kind == 'home' else {'@id': org_id},
    }
    if page_data.get('meta_description') or page_data.get('description'):
        webpage['description'] = page_data.get('meta_description') or page_data.get('description')
    if kind != 'post':
        # posts get their BlogPosting node from the dedicated branch below
        nodes.append(webpage)
    if kind != 'home':
        # BreadcrumbList on every public page except the homepage; crumbs
        # reflect the page's real path. No fake data — names come from the
        # page's own content.
        crumbs = [('Home', '/')]
        if kind in ('services', 'service'):
            crumbs.append(('Services', '/services/'))
        elif kind in ('blog', 'post'):
            crumbs.append(('Blog', '/blog/'))
        if kind == 'about':
            crumbs.append(('About', extra.get('path', '/about-us/')))
        elif kind == 'contact':
            crumbs.append(('Contact', extra.get('path', '/contact/')))
        elif kind == 'service':
            crumbs.append((page_data.get('title') or 'Service',
                           extra.get('path', '/')))
        elif kind == 'post':
            crumbs.append((extra.get('fm', {}).get('title') or 'Post',
                           extra.get('path', '/')))
        nodes.append({
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': i + 1, 'name': name,
                 'item': SITE_URL + url_path}
                for i, (name, url_path) in enumerate(crumbs)
            ],
        })
    if kind == 'services':
        nodes.append({
            '@type': 'ItemList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': i + 1,
                 'item': {'@type': 'Service', '@id': SITE_URL + '/services/%s/#service' % slug,
                          'name': title, 'url': SITE_URL + '/services/%s/' % slug}}
                for i, (slug, title, _, _) in enumerate(_service_list())
            ],
        })
    elif kind == 'service':
        svc = {'@type': 'Service', '@id': page_url + '#service',
               'name': page_data.get('title'), 'url': page_url,
               'provider': {'@id': org_id}}
        if page_data.get('meta_description'):
            svc['description'] = page_data['meta_description']
        img = _abs_url(page_data.get('image'))
        if img:
            svc['image'] = img
        nodes.append(svc)
    elif kind == 'blog':
        nodes.append({
            '@type': 'ItemList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': i + 1,
                 'item': {'@type': 'BlogPosting',
                          '@id': SITE_URL + '/blog/%s/#article' % fm['slug'],
                          'headline': fm.get('title'),
                          'url': SITE_URL + '/blog/%s/' % fm['slug'],
                          'datePublished': fm.get('date')}}
                for i, fm in enumerate(extra.get('posts', []))
            ],
        })
    elif kind == 'post':
        fm = extra.get('fm', {})
        article = {'@type': 'BlogPosting', '@id': page_url + '#article',
                   'headline': fm.get('title'), 'url': page_url,
                   'author': {'@id': org_id}, 'publisher': {'@id': org_id}}
        if fm.get('description'):
            article['description'] = fm['description']
        if fm.get('date'):
            article['datePublished'] = fm['date']
        src = fm.get('_src')
        if src and os.path.exists(src):
            article['dateModified'] = date.fromtimestamp(os.path.getmtime(src)).isoformat()
        img = _abs_url(fm.get('image'))
        if img:
            article['image'] = img
        nodes.append(article)
    return {'@context': 'https://schema.org', '@graph': nodes}

def apply_schema(html, kind, page_data, sdata, extra=None):
    tag = ('<script type="application/ld+json">\n'
           + json.dumps(build_jsonld(kind, page_data, sdata, extra), indent=2)
           + '\n</script>')
    if '<script type="application/ld+json">' in html:
        html = re.sub(r'<script type="application/ld\+json">.*?</script>',
                      lambda m: tag, html, flags=re.S)
    else:
        html = html.replace('</head>', tag + '\n</head>', 1)
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
    fm['_src'] = path
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

PAGE_KIND = {
    'index.html': 'home',
    'about-us/index.html': 'about',
    'services/index.html': 'services',
    'contact/index.html': 'contact',
}

def _url_path(rel):
    return '/' if rel == 'index.html' else '/' + rel[:-len('/index.html')] + '/'

# Base URL used for sitemap.xml, canonicals, and share tags.
# TODO: switch to the real domain (e.g. https://vitalrankdigital.com) once connected.
SITE_URL = 'https://www.vitalrankdigital.com'

def build_sitemap(posts):
    """Regenerate the sitemap set Yoast-style: sitemap.xml is an index that
    points at one child sitemap per content type (page / service / post),
    each derived from the same sources the build uses, so any new or removed
    page is reflected automatically on the next build."""
    groups = {'page': [], 'service': [], 'post': []}
    def add(group, url_path, src_path, priority, changefreq):
        if src_path and os.path.exists(src_path):
            lastmod = date.fromtimestamp(os.path.getmtime(src_path)).isoformat()
        else:
            lastmod = date.today().isoformat()
        groups[group].append((url_path, lastmod, priority, changefreq))
    for rel, content_path in PAGE_MAP.items():
        url_path = '/' if rel == 'index.html' else '/' + rel[:-len('/index.html')] + '/'
        add('page', url_path, os.path.join(ROOT, content_path),
            '1.0' if rel == 'index.html' else '0.8', 'weekly')
    add('page', '/blog/', os.path.join(ROOT, 'content', 'pages', 'blog.yml'),
        '0.7', 'weekly')
    for md_path in sorted(glob.glob(os.path.join(ROOT, 'content', 'services', '*.md'))):
        slug = os.path.splitext(os.path.basename(md_path))[0]
        if os.path.exists(os.path.join(ROOT, 'services', slug, 'index.html')):
            add('service', '/services/%s/' % slug, md_path, '0.8', 'monthly')
    for fm in posts:
        add('post', '/blog/%s/' % fm['slug'], fm.get('_src'), '0.6', 'monthly')

    def urlset(entries):
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for url_path, lastmod, priority, changefreq in entries:
            lines.append('  <url>')
            lines.append('    <loc>%s%s</loc>' % (SITE_URL, url_path))
            lines.append('    <lastmod>%s</lastmod>' % lastmod)
            lines.append('    <changefreq>%s</changefreq>' % changefreq)
            lines.append('    <priority>%s</priority>' % priority)
            lines.append('  </url>')
        lines.append('</urlset>')
        return '\n'.join(lines) + '\n'

    total = 0
    children = []
    for group in ('page', 'service', 'post'):
        entries = groups[group]
        if not entries:
            continue
        fname = '%s-sitemap.xml' % group
        open(os.path.join(ROOT, fname), 'w', encoding='utf-8').write(urlset(entries))
        children.append((fname, max(e[1] for e in entries)))
        total += len(entries)
        print('wrote %s (%d urls)' % (fname, len(entries)))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for fname, lastmod in children:
        lines.append('  <sitemap>')
        lines.append('    <loc>%s/%s</loc>' % (SITE_URL, fname))
        lines.append('    <lastmod>%s</lastmod>' % lastmod)
        lines.append('  </sitemap>')
    lines.append('</sitemapindex>')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(
        '\n'.join(lines) + '\n')
    print('wrote sitemap.xml (index, %d urls total)' % total)
    # keep robots.txt pointing at the sitemap
    robots_path = os.path.join(ROOT, 'robots.txt')
    sitemap_line = 'Sitemap: %s/sitemap.xml' % SITE_URL
    if os.path.exists(robots_path):
        robots = open(robots_path, encoding='utf-8').read()
        if 'Sitemap:' in robots:
            robots = re.sub(r'^Sitemap:.*$', sitemap_line, robots, flags=re.M)
        else:
            robots = robots.rstrip('\n') + '\n\n' + sitemap_line + '\n'
        open(robots_path, 'w', encoding='utf-8').write(robots)
        print('updated robots.txt')

def build_page(rel, content_path, sdata, posts):
    html_path = os.path.join(ROOT, rel)
    if not os.path.exists(html_path):
        return
    page_data = load_yaml_file(os.path.join(ROOT, content_path))
    html = open(html_path, encoding='utf-8').read()
    html = inject_chrome(html, sdata, posts)
    html = apply_markers(html, page_data, sdata, posts)
    html = apply_meta(html, page_data)
    html = apply_schema(html, PAGE_KIND[rel], page_data, sdata,
                        {'path': _url_path(rel), 'posts': posts})
    html = apply_head_tags(html, _url_path(rel), page_data,
                           og_image=page_data.get('hero_image'), og_type='website')
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
    html = apply_schema(html, 'service', page_data, sdata,
                        {'path': '/services/%s/' % slug})
    html = apply_head_tags(html, '/services/%s/' % slug, fm,
                           og_image=fm.get('image'), og_type='website')
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
        html = apply_schema(html, 'post', dict(fm), sdata,
                            {'path': '/blog/%s/' % fm['slug'], 'fm': fm})
        html = apply_head_tags(html, '/blog/%s/' % fm['slug'], dict(fm),
                               og_image=fm.get('image'), og_type='article')
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(html)
        print('wrote blog/%s/index.html' % fm['slug'])

    blog_data = load_yaml_file(os.path.join(ROOT, 'content', 'pages', 'blog.yml'))
    home_data = load_yaml_file(os.path.join(ROOT, 'content', 'pages', 'home.yml'))
    html = apply_markers(inject_chrome(render_index(posts), sdata, posts), blog_data, sdata, posts)
    html = apply_meta(html, blog_data)
    html = apply_schema(html, 'blog', blog_data, sdata,
                        {'path': '/blog/', 'posts': posts})
    html = apply_head_tags(html, '/blog/', blog_data,
                           og_image=home_data.get('hero_image'), og_type='website')
    open(os.path.join(ROOT, 'blog', 'index.html'), 'w', encoding='utf-8').write(html)
    print('wrote blog/index.html (%d posts)' % len(posts))

    build_sitemap(posts)

if __name__ == '__main__':
    main()
