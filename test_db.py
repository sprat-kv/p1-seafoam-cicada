import os, psycopg
from dotenv import load_dotenv
load_dotenv()
u=os.environ['DATABASE_URL']
print('DATABASE_URL=',u)
conn=psycopg.connect(u)
cur=conn.cursor()
cur.execute("select current_database(), current_user, inet_server_addr(), inet_server_port()")
print('TARGET=',cur.fetchone())
cur.execute("select table_schema, table_name from information_schema.tables where table_schema not in ('pg_catalog','information_schema') order by 1,2")
rows=cur.fetchall()
print('TABLES=',rows)
conn.close()