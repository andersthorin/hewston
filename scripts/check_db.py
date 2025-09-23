import sqlite3
c=sqlite3.connect('data/catalog.sqlite')
print('runs cols:', [x[1] for x in c.execute('PRAGMA table_info(runs)')])
print('datasets cols:', [x[1] for x in c.execute('PRAGMA table_info(datasets)')])
print('run_metrics exists:', bool(c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='run_metrics'").fetchone()))

