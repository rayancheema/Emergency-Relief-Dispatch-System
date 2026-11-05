import math
import sqlite3
DB_Name = 'relief_system.db'

def init_db():
    conn = sqlite3.connect(DB_Name)
    cur = conn.cursor()
    
    # Table 1: Inventory
    cur.execute(''' 
        CREATE TABLE IF NOT EXISTS inventory(
            warehouse_id TEXT,
            item TEXT,
            quantity INTEGER NOT NULL CHECK (quantity >= 0),
            PRIMARY KEY (warehouse_id, item)
        )
    ''')
    
    # Table 2: Requests
    cur.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shelter_id TEXT,
            item TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            allocated_quantity INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Pending',
            urgency TEXT NOT NULL CHECK (
                urgency IN ('Critical', 'High', 'Moderate')
            ),
            FOREIGN KEY (shelter_id) REFERENCES shelters (shelter_id)
        )
    ''')

    # Table 3: Shelters
    cur.execute(''' 
        CREATE TABLE IF NOT EXISTS shelters(
            shelter_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            priority TEXT NOT NULL CHECK (priority IN ('Critical', 'High', 'Moderate')),
            location_coordinates TEXT
        )
    ''')
    
    # Table 4: Allocation Logs
    cur.execute(''' 
        CREATE TABLE IF NOT EXISTS allocation_logs(
            allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            shelter_id TEXT,
            warehouse_id TEXT,
            item TEXT,
            quantity_allocated INTEGER,
            allocation_time TEXT
        )
    ''')

    # Table 5: Hospitals
    cur.execute(''' 
        CREATE TABLE IF NOT EXISTS hospitals(
            hospital_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location_coordinates TEXT
        )
    ''')
    
    # Table 6: Doctors
    cur.execute(''' 
        CREATE TABLE IF NOT EXISTS doctors(
            doctor_id TEXT PRIMARY KEY,
            hospital_id TEXT,
            speciality TEXT NOT NULL,
            availability_status TEXT NOT NULL CHECK (availability_status IN ('Available', 'Unavailable'))
        )
    ''')
    
    # Table 7: Medic Requests (Added speciality column for matching patient needs)
    cur.execute(''' 
        CREATE TABLE IF NOT EXISTS medic_requests(
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shelter_id TEXT,
            hospital_id TEXT,
            doctor_id TEXT,
            speciality TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            FOREIGN KEY (shelter_id) REFERENCES shelters (shelter_id),
            FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id)
        )
    ''')
    
    # Master Items table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS master_items (
            item_name TEXT PRIMARY KEY
        )
    ''')
    
    # Master Warehouses table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS master_warehouses (
            warehouse_id TEXT PRIMARY KEY,
            location TEXT
        )
    ''')
    conn.commit()
    conn.close()

#=============================================================
#              Functions for the Shelters 
#=============================================================

def add_shelter(shelter_id, name, priority, location_coordinates):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("INSERT OR REPLACE INTO shelters (shelter_id, name, priority, location_coordinates) VALUES (?, ?, ?, ?)", (shelter_id, name, priority, location_coordinates))
    conn.commit()
    conn.close()

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

def get_all_inventory():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("SELECT * FROM inventory")
    items = cr.fetchall()
    conn.close()
    return items

def update_inventory_stock(warehouse_id, item, quantity):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("UPDATE inventory SET quantity = ? WHERE warehouse_id = ? AND item = ?", (quantity, warehouse_id, item))
    conn.commit()
    conn.close()

#=============================================================
#              Functions for the Requests 
#=============================================================

def add_request(shelter_id, item, quantity, urgency):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("INSERT INTO requests (shelter_id, item, quantity, urgency) VALUES (?, ?, ?, ?)", (shelter_id, item, quantity, urgency))
    conn.commit()
    conn.close()

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
        END,
        request_id ASC
    ''')
    requests_list = cr.fetchall()
    conn.close()
    return requests_list

def allocate_inventory():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("""
        SELECT request_id, shelter_id, item, quantity,
               allocated_quantity, urgency
        FROM requests
        ORDER BY CASE urgency
            WHEN 'Critical' THEN 1
            WHEN 'High' THEN 2
            WHEN 'Moderate' THEN 3
            ELSE 4
        END,
        request_id ASC
    """)
    requests_list = cr.fetchall()
    for request in requests_list:
        request_id, shelter_id, item, quantity, allocated_quantity, urgency = request
        remaining = quantity - allocated_quantity

        if remaining <= 0:
            continue

        cr.execute("""
            SELECT warehouse_id, quantity
            FROM inventory
            WHERE LOWER(TRIM(item)) = LOWER(TRIM(?))
              AND quantity > 0
            ORDER BY warehouse_id
        """, (item,))
        warehouses = cr.fetchall()

        for warehouse_id, stock in warehouses:
            if remaining <= 0:
                break

            allocated = min(remaining, stock)

            cr.execute("""
                UPDATE inventory
                SET quantity = quantity - ?
                WHERE warehouse_id = ?
                  AND LOWER(TRIM(item)) = LOWER(TRIM(?))
            """, (allocated, warehouse_id, item))

            cr.execute("""
                INSERT INTO allocation_logs
                (request_id, shelter_id, warehouse_id, item,
                 quantity_allocated, allocation_time)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (request_id, shelter_id, warehouse_id, item, allocated))

            allocated_quantity += allocated
            remaining -= allocated

        if allocated_quantity >= quantity:
            status = "Fulfilled"
        elif allocated_quantity > 0:
            status = "Partially Fulfilled"
        else:
            status = "Pending"

        cr.execute("""
            UPDATE requests
            SET allocated_quantity = ?, status = ?
            WHERE request_id = ?
        """, (allocated_quantity, status, request_id))
    conn.commit()
    conn.close()

#=============================================================
#              Functions for the Hospitals 
#=============================================================

def add_hospital(hospital_id, name, location_coordinates):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("INSERT OR REPLACE INTO hospitals (hospital_id, name, location_coordinates) VALUES (?, ?, ?)", (hospital_id, name, location_coordinates))
    conn.commit()
    conn.close()
    
def get_all_hospitals():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("SELECT * FROM hospitals")
    hospitals = cr.fetchall()
    conn.close()
    return hospitals

#=============================================================
#              Functions for the Doctors 
#=============================================================

def add_doctor(doctor_id, speciality, availability_status, hospital_id):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("""
        INSERT OR REPLACE INTO doctors (doctor_id, hospital_id, speciality, availability_status) 
        VALUES (?, ?, ?, ?)
    """, (doctor_id, hospital_id, speciality, availability_status))
    conn.commit()
    conn.close()
    
def get_all_doctors():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("SELECT * FROM doctors")
    doctors = cr.fetchall()
    conn.close()
    return doctors

def _parse_coordinates(coordinates):
   if not isinstance(coordinates, str):
       raise ValueError("Coordinates must be two numeric values separated by a comma.")

   parts = coordinates.split(",")
   if len(parts) != 2:
       raise ValueError("Coordinates must be two numeric values separated by a comma.")

   try:
       x, y = (float(part.strip()) for part in parts)
   except ValueError as exc:
       raise ValueError(
           "Coordinates must be two numeric values separated by a comma."
       ) from exc

   if not math.isfinite(x) or not math.isfinite(y):
       raise ValueError("Coordinates must be finite numbers.")
   return x, y

#=============================================================
#              Functions for the allocation of medic support 
#=============================================================

def add_medic_request(shelter_id, hospital_id, doctor_id, speciality):
   conn = sqlite3.connect(DB_Name)
   cr = conn.cursor()
   cr.execute("INSERT INTO medic_requests (shelter_id, hospital_id, doctor_id, speciality, status) VALUES (?, ?, ?, ?, 'Pending')", (shelter_id, hospital_id, doctor_id, speciality))
   conn.commit()
   conn.close()

def allocate_medics(shelter_id, speciality):
   """
   Finds the nearest available doctor matching the requested specialty 
   relative to the shelter's coordinates, allocates them, and updates their status.
   """
   conn = sqlite3.connect(DB_Name)
   try:
       with conn:
           conn.execute("BEGIN IMMEDIATE")
           cr = conn.cursor()

           cr.execute(
               "SELECT location_coordinates FROM shelters WHERE shelter_id = ?",
               (shelter_id,),
           )
           shelter = cr.fetchone()
           if shelter is None:
               raise ValueError(f"Shelter not found: {shelter_id}")
           shelter_x, shelter_y = _parse_coordinates(shelter[0])

           # Query available doctors matching the requested specialty
           cr.execute("""
               SELECT h.hospital_id, h.location_coordinates, d.doctor_id
               FROM hospitals h
               JOIN doctors d ON h.hospital_id = d.hospital_id
               WHERE h.location_coordinates IS NOT NULL
                 AND d.availability_status = 'Available'
                 AND LOWER(TRIM(d.speciality)) = LOWER(TRIM(?))
           """, (speciality,))
           
           available_rows = cr.fetchall()

           candidates = []
           for hospital_id, coordinates, doctor_id in available_rows:
               hospital_x, hospital_y = _parse_coordinates(coordinates)
               distance = math.sqrt(
                   (hospital_x - shelter_x) ** 2
                   + (hospital_y - shelter_y) ** 2
               )
               candidates.append((distance, hospital_id, doctor_id))

           if not candidates:
               return None  # No available doctors found matching that specialty

           # Sort candidates by distance to find the nearest available doctor
           candidates.sort(key=lambda x: x[0])
           distance, hospital_id, doctor_id = candidates[0]

           cr.execute("""
               INSERT INTO medic_requests (shelter_id, hospital_id, doctor_id, speciality, status)
               VALUES (?, ?, ?, ?, 'Allocated')
           """, (shelter_id, hospital_id, doctor_id, speciality))
           
           cr.execute("""
               UPDATE doctors
               SET availability_status = 'Unavailable'
               WHERE doctor_id = ? AND availability_status = 'Available'
           """, (doctor_id,))

           return hospital_id, doctor_id, distance
   finally:
       conn.close()
       
def get_all_medic_requests():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("""
        SELECT request_id, shelter_id, hospital_id, doctor_id, speciality, status 
        FROM medic_requests
    """)
    data = cr.fetchall()
    
    conn.close()
    return data
def get_allocation_history():
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            allocation_logs.allocation_id,
            allocation_logs.request_id,
            allocation_logs.shelter_id,
            allocation_logs.warehouse_id,
            allocation_logs.item,
            allocation_logs.quantity_allocated,
            allocation_logs.allocation_time
        FROM allocation_logs
        ORDER BY allocation_logs.allocation_id DESC
    """)
    history = cursor.fetchall()
    conn.close()
    return history

# --- MASTER ITEMS TABLE & FUNCTIONS ---
def init_items_table():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute('''
        CREATE TABLE IF NOT EXISTS master_items (
            item_name TEXT PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

def add_master_item(item_name):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("INSERT OR IGNORE INTO master_items (item_name) VALUES (?)", (item_name.strip(),))
    conn.commit()
    conn.close()

def get_all_master_items():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("SELECT item_name FROM master_items ORDER BY item_name ASC")
    items = [row[0] for row in cr.fetchall()]
    conn.close()
    return items

def delete_master_item(item_name):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("DELETE FROM master_items WHERE item_name = ?", (item_name,))
    conn.commit()
    conn.close()

# --- MASTER WAREHOUSES TABLE & FUNCTIONS ---
def init_warehouses_table():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute('''
        CREATE TABLE IF NOT EXISTS master_warehouses (
            warehouse_id TEXT PRIMARY KEY,
            location TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_master_warehouse(warehouse_id, location=""):
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("INSERT OR IGNORE INTO master_warehouses (warehouse_id, location) VALUES (?, ?)", (warehouse_id.strip(), location.strip()))
    conn.commit()
    conn.close()

def get_all_master_warehouses():
    conn = sqlite3.connect(DB_Name)
    cr = conn.cursor()
    cr.execute("SELECT warehouse_id FROM master_warehouses ORDER BY warehouse_id ASC")
    warehouses = [row[0] for row in cr.fetchall()]
    conn.close()
    return warehouses

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")