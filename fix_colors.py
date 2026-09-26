p = r'D:\projects\pms\project\predictive-maintenance\08_streamlit_app.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()
replacements = {
    'COLORS["success"]': 'SUCCESS',
    'COLORS["warning"]': 'WARNING',
    'COLORS["danger"]': 'DANGER',
    'COLORS["orange"]': 'ORANGE',
    'COLORS["accent"]': 'ACCENT',
    'COLORS["text"]': 'T["text"]',
    'COLORS["muted"]': 'T["muted"]',
}
for old, new in replacements.items():
    c = c.replace(old, new)
with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
