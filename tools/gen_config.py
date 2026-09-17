#!/usr/bin/env python3
"""Generate admin/config.yml from the actual content files.
Run: python3 tools/gen_config.py
"""
import os, yaml, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def S(label, name, **kw):
    d = {'label': label, 'name': name, 'widget': 'string'}
    d.update(kw); return d
def T(label, name, **kw):
    d = {'label': label, 'name': name, 'widget': 'text'}
    d.update(kw); return d
def M(label, name, **kw):
    d = {'label': label, 'name': name, 'widget': 'markdown'}
    d.update(kw); return d
def IMG(label, name, **kw):
    d = {'label': label, 'name': name, 'widget': 'image', 'required': False}
    d.update(kw); return d
def LST(label, name, fields, **kw):
    d = {'label': label, 'name': name, 'widget': 'list', 'fields': fields}
    d.update(kw); return d

def seo_fields():
    return [
        S('SEO title', 'seo_title', hint='Shown in browser tab and Google results'),
        T('Meta description', 'meta_description', hint='150-160 characters for Google'),
        S('OG title', 'og_title', required=False),
        T('OG description', 'og_description', required=False),
    ]

def hero_fields(with_subtitle=True):
    f = [S('Hero title', 'hero_title'),
         IMG('Hero image', 'hero_image'),
         S('Hero image alt text', 'hero_image_alt', required=False)]
    if with_subtitle:
        f.insert(1, T('Hero subtitle', 'hero_subtitle'))
    return f

# ---------------------------------------------------------------- page files
def page_file(name, label, fields):
    return {'name': name, 'label': label,
            'file': 'content/pages/%s.yml' % name, 'fields': fields}

home_fields = seo_fields() + hero_fields() + [
    S('Hero button 1 label', 'hero_btn1'),
    S('Hero button 2 label', 'hero_btn2'),
    LST('Client logos', 'client_logos', [
        S('Name', 'name'), T('Logo SVG code', 'icon')]),
    S('Services section label', 'services_label'),
    S('Services section title', 'services_title'),
    T('Services intro', 'services_intro'),
    LST('Service cards', 'service_cards', [
        S('Title', 'title'), S('Page URL', 'url'),
        IMG('Card image', 'image'), S('Image alt', 'image_alt'),
        S('CSS class', 'css_class', required=False)]),
    S('Custom CTA title', 'custom_cta_title'),
    S('Custom CTA button', 'custom_cta_btn'),
    IMG('Approach image', 'approach_image'),
    S('Approach image alt', 'approach_image_alt', required=False),
    S('Approach stat label', 'approach_fc_label'),
    S('Approach stat value', 'approach_fc_value'),
    S('Approach label', 'approach_label'),
    S('Approach title', 'approach_title'),
    T('Approach text', 'approach_lead'),
    LST('Approach checklist', 'approach_points', [T('Point', 'text')]),
    IMG('Banner image', 'banner_image'),
    S('Banner image alt', 'banner_image_alt', required=False),
    S('Banner title', 'banner_title'),
    S('Banner link label', 'banner_link'),
    S('Why-us label', 'why_label'),
    S('Why-us title', 'why_title'),
    T('Why-us intro', 'why_lead'),
    LST('Why-us cards', 'why_cards', [
        S('Title', 'title'), T('Text', 'text'),
        S('Link label', 'link_text'), S('Link URL', 'url'),
        T('Icon SVG code', 'icon')]),
    S('Process title', 'process_title'),
    T('Process text', 'process_text'),
    S('Process button label', 'process_btn'),
    LST('Process steps', 'process_steps', [
        S('Number', 'num'), S('Title', 'title'),
        T('Text', 'text'), S('Link URL', 'url', required=False)]),
    IMG('Commitment image', 'commit_image'),
    S('Commitment image alt', 'commit_image_alt', required=False),
    S('Commitment stat 1 value', 'commit_fc1_value'),
    S('Commitment stat 1 label', 'commit_fc1_label'),
    S('Commitment stat 2 value', 'commit_fc2_value'),
    S('Commitment stat 2 label', 'commit_fc2_label'),
    S('Commitment label', 'commit_label'),
    S('Commitment title', 'commit_title'),
    T('Commitment text', 'commit_lead'),
    S('Commitment button', 'commit_btn'),
    S('Testimonials label', 'testi_label'),
    S('Testimonials title', 'testi_title'),
    T('Testimonials intro', 'testi_text'),
    S('Blog section label', 'blog_label'),
    S('Blog section title', 'blog_title'),
    T('Blog section intro', 'blog_lead'),
]

about_fields = seo_fields() + hero_fields(with_subtitle=False) + [
    S('Journey label', 'journey_label'),
    S('Journey title', 'journey_title'),
    T('Journey text', 'journey_text'),
    IMG('Signature image', 'signature_image'),
    S('Signature image alt', 'signature_image_alt', required=False),
    S('Values title', 'values_title'),
    T('Values text', 'values_text'),
    S('Approach title', 'approach_title'),
    T('Approach text', 'approach_text'),
    IMG('Office image', 'office_image'),
    S('Office image alt', 'office_image_alt', required=False),
    LST('Stats', 'stats', [S('Number', 'num'), S('Label', 'label')]),
    S('Team label', 'team_label'),
    S('Team title', 'team_title'),
    T('Team intro', 'team_text'),
    LST('Team members', 'team', [
        S('Name', 'name'), S('Role', 'role'),
        IMG('Photo', 'image'), S('Photo alt', 'image_alt', required=False)]),
]

services_fields = seo_fields() + hero_fields(with_subtitle=False) + [
    S('Services label', 'services_label'),
    S('Services title', 'services_title'),
    T('Services intro', 'services_intro'),
    LST('Service cards', 'service_cards', [
        S('Title', 'title'), S('Page URL', 'url'),
        IMG('Card image', 'image'), S('Image alt', 'image_alt')]),
]

contact_fields = seo_fields() + hero_fields(with_subtitle=False) + [
    S('Contact label', 'contact_label'),
    S('Contact title', 'contact_title'),
    T('Contact intro', 'contact_text'),
    S('Name field placeholder', 'form_name_ph'),
    S('Email field placeholder', 'form_email_ph'),
    S('Message field placeholder', 'form_msg_ph'),
    S('Submit button label', 'form_button'),
    T('Form note', 'form_note'),
]

blog_fields = seo_fields() + [
    S('Blog label', 'blog_label'),
    S('Blog title', 'blog_title'),
    T('Blog subtitle', 'blog_subtitle', hint='HTML allowed, e.g. <br> for line break'),
    T('Blog intro', 'blog_lead'),
]

def service_file(slug, label):
    return {'name': 'svc_' + slug.replace('-', '_'), 'label': label,
            'file': 'content/services/%s.md' % slug,
            'fields': seo_fields() + [
                S('Hero title', 'hero_title'),
                T('Hero subtitle', 'hero_subtitle'),
                IMG('Hero image', 'hero_image'),
                S('Hero image alt', 'hero_image_alt', required=False),
                S('Sidebar title', 'sidebar_title'),
                LST('Sidebar points', 'sidebar_points', [T('Point', 'text')]),
                S('Sidebar CTA title', 'sidebar_cta_title'),
                T('Sidebar CTA text', 'sidebar_cta_text'),
                M('Page content', 'body'),
            ]}

site_fields = [
    S('Site name', 'site_name'),
    T('Tagline', 'tagline'),
    T('Footer text', 'footer_text'),
    IMG('Logo', 'logo'),
    S('Logo alt', 'logo_alt', required=False),
    IMG('Footer logo (white)', 'logo_white'),
    S('Footer logo alt', 'logo_white_alt', required=False),
    S('Nav: Home', 'nav_home'), S('Nav: About', 'nav_about'),
    S('Nav: Services', 'nav_services'), S('Nav: Blog', 'nav_blog'),
    S('Nav: Contact', 'nav_contact'),
    S('CTA title', 'cta_title'), S('CTA button', 'cta_button'),
    LST('Social links', 'social', [
        S('Label', 'label'), S('URL', 'url'), T('Icon SVG code', 'icon')]),
    S('Footer column 1 title', 'footer_col1_title'),
    LST('Footer column 1 links', 'footer_col1', [S('Label', 'label'), S('URL', 'url')]),
    S('Footer column 2 title', 'footer_col2_title'),
    LST('Footer column 2 links', 'footer_col2', [S('Label', 'label'), S('URL', 'url')]),
    S('Footer column 3 title', 'footer_col3_title'),
    LST('Footer column 3 links', 'footer_col3', [S('Label', 'label'), S('URL', 'url')]),
]

SERVICE_PAGES = [
    ('seo-consulting-services', 'SEO Consulting'),
    ('technical-seo-services', 'Technical SEO'),
    ('enterprise-seo-services-for-large-sites', 'Enterprise SEO'),
    ('b2b-seo-services', 'B2B SEO'),
    ('local-seo-services', 'Local SEO'),
    ('ecommerce-seo-services', 'Ecommerce SEO'),
]

config = {
    'backend': {
        'name': 'github',
        'repo': 'vtalwar9/vitalrank-website',
        'branch': 'main',
        'base_url': 'https://vitalrank.netlify.app',
        'auth_endpoint': 'api/auth',
    },
    'media_folder': 'assets/img',
    'public_folder': '/assets/img',
    'publish_mode': 'editorial_workflow',
    'collections': [
        {'name': 'settings', 'label': 'Site settings', 'files': [
            {'name': 'site', 'label': 'General', 'file': 'content/settings/site.yml',
             'fields': site_fields},
        ]},
        {'name': 'pages', 'label': 'Pages', 'files': [
            page_file('home', 'Home', home_fields),
            page_file('about', 'About', about_fields),
            page_file('services', 'Services', services_fields),
            page_file('contact', 'Contact', contact_fields),
            page_file('blog', 'Blog', blog_fields),
        ]},
        {'name': 'service_pages', 'label': 'Service pages',
         'files': [service_file(s, l) for s, l in SERVICE_PAGES]},
        {'name': 'testimonials', 'label': 'Testimonials', 'files': [
            {'name': 'all', 'label': 'All testimonials',
             'file': 'content/testimonials.yml',
             'fields': [LST('Testimonials', 'testimonials', [
                 T('Quote', 'quote'), S('Name', 'name'), S('Role', 'role')])]},
        ]},
        {'name': 'blog_posts', 'label': 'Blog posts',
         'folder': 'content/blog', 'create': True, 'slug': '{{slug}}',
         'fields': [
             S('Title', 'title'),
             {'label': 'Publish date', 'name': 'date', 'widget': 'datetime'},
             T('Description', 'description'),
             IMG('Card image', 'image'),
             S('Image alt', 'image_alt', required=False),
             M('Body', 'body'),
         ]},
    ],
}

out = os.path.join(ROOT, 'admin', 'config.yml')
header = ("# Decap CMS configuration — ViTalRank content manager (served at /admin/)\n"
          "# Sign in with GitHub via the site's OAuth proxy (/api/auth + /api/callback),\n"
          "# then edit at https://vitalrank.netlify.app/admin/\n"
          "# Generated by tools/gen_config.py — edit that script, not this file.\n\n")
with open(out, 'w', encoding='utf-8') as f:
    f.write(header)
    yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
print('wrote', out)
import json as _json
out_json = os.path.join(ROOT, 'admin', 'config.json')
with open(out_json, 'w', encoding='utf-8') as f:
    _json.dump(config, f, ensure_ascii=False, indent=1)
print('wrote', out_json)
