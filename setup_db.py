import psycopg2

def setup():
    # 1. Connect to default postgres DB
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='postgres', dbname='postgres')
    conn.autocommit = True
    cur = conn.cursor()

    # Create chinook database if it doesn't exist
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'chinook'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE chinook;")
        print("Created database 'chinook'")
    else:
        print("Database 'chinook' already exists")

    # Create readonly role if it doesn't exist
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'readonly'")
    if not cur.fetchone():
        cur.execute("CREATE ROLE readonly WITH LOGIN PASSWORD 'readonly_pw';")
        print("Created role 'readonly'")
    else:
        print("Role 'readonly' already exists")

    conn.close()

    # 2. Connect to chinook and apply schema and permissions
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='postgres', dbname='chinook')
    conn.autocommit = True
    cur = conn.cursor()

    # Check if tables exist
    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'artists'")
    if not cur.fetchone():
        with open('seed/01_chinook.sql', 'r', encoding='utf-8') as f:
            sql1 = f.read()
        cur.execute(sql1)
        print("Loaded seed/01_chinook.sql schema and data")
    else:
        print("Tables already exist in chinook")

    with open('seed/02_readonly.sql', 'r', encoding='utf-8') as f:
        sql2 = f.read()
    
    for stmt in sql2.split(';'):
        stmt = stmt.strip()
        if not stmt or 'CREATE ROLE' in stmt:
            continue
        try:
            cur.execute(stmt)
        except Exception as e:
            print(f"Notice on statement: {e}")
    print("Permissions granted to 'readonly' role")
    conn.close()

if __name__ == '__main__':
    setup()
