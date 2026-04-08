import sys, re

with open(sys.argv[1]) as f:
    lines = f.read().splitlines()

subject = lines[0]
sections = []
current_section = None
current_items = []

for line in lines[1:]:
    if line.startswith('=== ') and line.endswith(' ==='):
        if current_section is not None:
            sections.append((current_section, current_items))
        current_section = line[4:-4]
        current_items = []
    elif line.startswith('\u2022 ') or line.startswith('- '):
        current_items.append(line[2:])

if current_section is not None:
    sections.append((current_section, current_items))

colors = {
    'ROBOTICS & AI': '#6B3FA0',
    'RESEARCH': '#3A7BD5',
    'FUNDING & INVESTMENT': '#2E8B57',
    'COMPETITOR WATCH': '#B03A2E',
    'BAY AREA': '#D68910',
}

def linkify(text):
    return re.sub(r'(https?://[^\s<]+)', r'<a href="\1" style="color:#6B3FA0;text-decoration:none;">\1</a>', text)

section_html = ''
for title, items in sections:
    color = colors.get(title, '#555')
    rows = [i for i in items if i.strip()]
    items_html = ''.join('<li style="margin-bottom:8px;line-height:1.6;">' + linkify(i) + '</li>' for i in rows) if rows else '<li style="color:#999;font-style:italic;">No items.</li>'
    section_html += (
        '<div style="margin-bottom:28px;">'
        '<span style="background:' + color + ';color:white;padding:4px 10px;border-radius:3px;font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;">' + title + '</span>'
        '<ul style="margin:10px 0 0 0;padding-left:18px;color:#2c2c2c;font-size:14px;">' + items_html + '</ul>'
        '</div>'
    )

html = (
    '<!DOCTYPE html><html><head><meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>'
    '<body style="margin:0;padding:0;background:#f0f0f0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,sans-serif;">'
    '<div style="max-width:600px;margin:32px auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
    '<div style="background:#100720;padding:28px 36px;">'
    '<div style="font-size:10px;color:#C9B1E8;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:6px;">ART Lab</div>'
    '<div style="font-size:20px;color:#ffffff;font-weight:300;letter-spacing:0.5px;">' + subject + '</div>'
    '</div>'
    '<div style="padding:32px 36px;">' + section_html + '</div>'
    '<div style="background:#f9f9f9;padding:14px 36px;border-top:1px solid #ececec;">'
    '<p style="margin:0;font-size:11px;color:#aaa;">ART Lab &middot; AI Consumer Robotics &middot; San Francisco</p>'
    '</div></div></body></html>'
)

print(html)
