with open(r'D:\projects\pms\project\predictive-maintenance\08_streamlit_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}')
for i, line in enumerate(lines):
    if 'def page_' in line or ('# ' in line and '===' in line):
        print(f'  Line {i+1}: {line.strip()}')
