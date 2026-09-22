p = r'D:\projects\pms\project\predictive-maintenance\08_streamlit_app.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('st.divider()', 'st.markdown("---")')
with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
