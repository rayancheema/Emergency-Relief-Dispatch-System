import sqlite3
DB_Name = 'relief_system.db'
def init_db():
    conn = sqlite3.connect(DB_Name)
    cur = conn.cursor()
    #We have to create 3 tables according to specifications, therefore:
    #Table 1: Inventory
    cur.execute(''' 
        CREATE TABLE  IF NOT EXISTS inventory(
            warehouse_id TEXT,
            item TEXT,
            quantity INTEGER NOT NULL CHECK (quantity >= 0),
            PRIMARY KEY (warehouse_id, item)
        )
''')
    #table 2: Requests
    cur.execute('''
    CREATE TABLE IF NOT EXISTS requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        shelter_id TEXT,
        item TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        allocated_quantity INTEGER NOT NULL DEFAULT 0,
        TEXT NOT NULL DEFAULT 'Pending',
        urgency TEXT NOT NULL CHECK (
            urgency IN ('Critical', 'High', 'Moderate')
        ),
        FOREIGN KEY (shelter_id) REFERENCES shelters (shelter_id)
    )
''')

    #table 3: Shelters
    cur.execute(''' 
        CREATE TABLE  IF NOT EXISTS shelters(
            shelter_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            priority TEXT NOT NULL CHECK (priority IN ('Critical', 'High', 'Moderate')),
            location_coordinates TEXT
        )
''')
    #table 4: Logs
    cur.execute(''' 
        CREATE TABLE  IF NOT EXISTS allocation_logs(
                allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                shelter_id TEXT,
                warehouse_id TEXT,
                item TEXT,
                quantity_allocated INTEGER,
                allocation_time TEXT
        )
''')

    conn.commit()
    conn.close()

#=============================================================

def check_data():
    conn= sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("SELECT * FROM inventory")
    print(cr.fetchall())
    conn.close()


#=============================================================
#              Functions for the Shelters 
#=============================================================


# Define a function to add a shelter to the shelters table

def add_shelter(shelter_id, name,priority, location_coordinates):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("INSERT OR REPLACE INTO shelters (shelter_id, name, priority, location_coordinates) VALUES (?, ?, ?, ?)", (shelter_id, name, priority, location_coordinates))
    conn.commit()
    conn.close()

# Define a function to get details about all shelters

def get_all_shelters():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("SELECT * FROM shelters")
    shelters = cr.fetchall()
    conn.close()
    return shelters

#=============================================================
#              Functions for the Inventory 
#=============================================================

#Add item to inventory table

def add_inventory_item(warehouse_id, item, quantity):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("""
        INSERT INTO inventory (warehouse_id, item, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(warehouse_id, item)
        DO UPDATE SET quantity = quantity + excluded.quantity
    """, (warehouse_id, item, quantity))
    conn.commit()
    conn.close()

#Get all items from inventory table

def get_all_inventory():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("SELECT * FROM inventory")
    items = cr.fetchall()
    conn.close()
    return items

#Update item in inventory table

def update_inventory_stock(warehouse_id, item, quantity):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("UPDATE inventory SET quantity = ? WHERE warehouse_id = ? AND item = ?", (quantity, warehouse_id, item))
    conn.commit()
    conn.close()

#=============================================================
#              Functions for the Requests 
#=============================================================

#Define a request for shelter 

def add_request(shelter_id, item, quantity, urgency):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("INSERT INTO requests (shelter_id, item, quantity, urgency) VALUES (?, ?, ?, ?)", (shelter_id, item, quantity, urgency))
    conn.commit()
    conn.close()

# Order requests by urgency: Critical > High > Moderate

def get_sorted_requests():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()

    cr.execute('''
        SELECT * FROM requests
        ORDER BY CASE urgency
            WHEN 'Critical' THEN 1
            WHEN 'High' THEN 2
            WHEN 'Moderate' THEN 3
            ELSE 4
        END
    ''')

    requests_list = cr.fetchall()
    conn.close()

    return requests_list




if __name__ == "__main__":
    init_db()
    check_data()
    print("Database and tables initialized successfully!")
