import sqlite3
db = r'C:\dev\yannis-ai-build\labeling\labels.db'
c = sqlite3.connect(db)
tables = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
print('TABLES:', tables)
for t in tables:
    print('\n=== ' + t + ' ===')
    for col in c.execute('PRAGMA table_info(' + t + ')'):
        print('  ', col[1], col[2])
