import sys, re

with open(sys.argv[1]) as f:
    lines = f.read().splitlines()

subject = lines[0]

colors = {
    'ROBOTICS & AI': '#6B3FA0',
    'RESEARCH': '#3A7BD5',
    'FUNDING & INVESTMENT': '#2E8B57',
    'COMPETITOR WATCH': '#B03A2E',
    'BAY AREA': '#D68910',
}

def linkify(text):
    return re.sub(r'(https?://[^\s<]+)', r'<a href="\1" style="color:#6B3FA0;text-decoration:none;">\1</a>', text)

body_html = ''
in_list = False

for line in lines[1:]:
    if line.startswith('=== ') and line.endswith(' ==='):
        if in_list:
            body_html += '</ul>'
            in_list = False
        title = line[4:-4]
        color = colors.get(title, '#555')
        body_html += (
            '<div style="margin-top:28px;margin-bottom:10px;">'
            '<span style="background:' + color + ';color:white;padding:4px 10px;border-radius:3px;'
            'font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;">' + title + '</span>'
            '</div>'
        )
    elif line.startswith('\u2022 ') or line.startswith('- '):
        if not in_list:
            body_html += '<ul style="margin:6px 0 0 0;padding-left:18px;color:#2c2c2c;font-size:14px;">'
            in_list = True
        body_html += '<li style="margin-bottom:8px;line-height:1.6;">' + linkify(line[2:]) + '</li>'
    elif line.strip():
        if in_list:
            body_html += '</ul>'
            in_list = False
        body_html += '<p style="margin:6px 0;font-size:13px;color:#666;font-style:italic;">' + linkify(line.strip()) + '</p>'

if in_list:
    body_html += '</ul>'

html = (
    '<!DOCTYPE html><html><head><meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>'
    '<body style="margin:0;padding:0;background:#f0f0f0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,sans-serif;">'
    '<div style="max-width:600px;margin:32px auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
    '<div style="background:#100720;padding:28px 36px;">'
    '<div style="font-size:10px;color:#C9B1E8;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:6px;">ART Lab</div>'
    '<div style="font-size:20px;color:#ffffff;font-weight:300;letter-spacing:0.5px;">' + subject + '</div>'
    '</div>'
    '<div style="padding:32px 36px;">' + body_html + '</div>'
    '<div style="background:#f9f9f9;padding:14px 36px;border-top:1px solid #ececec;">'
    '<p style="margin:0;font-size:11px;color:#aaa;">ART Lab \u00b7 AI Consumer Robotics \u00b7 San Francisco</p>'
    '</div></div></body></html>'
)

print(html)
