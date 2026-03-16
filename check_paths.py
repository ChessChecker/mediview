files = [
    'modules/module/module1_hcc/dashboard.py',
    'modules/module/module2_hedis/dashboard_hedis.py',
    'modules/module/module3_rates/dashboard_rates.py',
    'modules/module/module4_compliance/dashboard_compliance.py'
]

target = "DB_PATH = r'C:\\Users\\gtbru\\MediView\\data\\mediview.db'"

for f in files:
    content = open(f, encoding='utf-8').read()
    status = 'FOUND' if target in content else 'MISSING'
    print(f.split('/')[-1], ':', status)