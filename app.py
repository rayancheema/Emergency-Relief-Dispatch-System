# Importing Modules
from flask import Flask, render_template, request, redirect, url_for, Response
import json
import csv
import io
import db

app = Flask(__name__)

# Making the main dashboard displaying the inventory, shelters and the prioritized requests.

@app.route('/')
def home():
    search = request.args.get('search', '')

    inventory = db.get_all_inventory()
    shelters = db.get_all_shelters()
    requests_list = db.get_sorted_requests()
    
    # Fetching medical hospitals, doctors, and allocation history for the main dashboard view if needed
    hospitals = db.get_all_hospitals()
    doctors = db.get_all_doctors()

    if search:
        inventory = [
            item for item in inventory
            if search.lower() in item[1].lower()
        ]

    return render_template(
        'inventory.html',
        inventory=inventory,
        shelters=shelters,
        requests_list=requests_list,
        hospitals=hospitals,
        doctors=doctors,
        search=search
    )
        
# Route to add stock supplies to a warehouse.
@app.route("/add_inventory", methods=["GET", "POST"])
def add_inventory():
    error = ""
    
    all_inventory = db.get_all_inventory()
    warehouses = sorted(list(set(row[0] for row in all_inventory)))
    items = sorted(list(set(row[1] for row in all_inventory)))

    if request.method == "POST":
        warehouse_id = request.form["warehouse_id"]
        item = request.form["item"]
        quantity = request.form["quantity"]
        if not warehouse_id or not item or int(quantity) < 0:
            error = "Please enter valid warehouse stock values (quantity cannot be negative)."
        else: 
            quantity = int(quantity)
            db.add_inventory_item(warehouse_id, item, quantity)
            return redirect(url_for("home"))
            
    return render_template("add_inventory.html", error=error, warehouses=warehouses, items=items)

# Route to add a new shelter
@app.route("/add_shelter", methods=["GET", "POST"])
def add_shelter():
    if request.method == "POST":
        shelter_id = request.form["shelter_id"]
        name = request.form["name"]
        priority = request.form["priority"]
        coordinates = request.form["coordinates"]

        db.add_shelter(shelter_id, name, priority, coordinates)
        return redirect(url_for("home"))

    return render_template("add_shelter.html")

# Route for a new request
@app.route("/add_request", methods=["GET", "POST"])
def add_request():
    error = ""
    shelters = db.get_all_shelters()
    
    # Combine Master Items and existing Inventory items
    master_items = db.get_all_master_items()
    inventory_items = [row[1] for row in db.get_all_inventory()]
    items = sorted(list(set(master_items + inventory_items)))

    if request.method == "POST":
        shelter_id = request.form["shelter_id"]
        item = request.form["item"]
        qty = request.form["quantity"]
        urgency = request.form.get("urgency", "Moderate")
        
        if not shelter_id or not item or not qty or int(qty) <= 0:
            error = "Please fill out all request fields correctly."
        else:
            db.add_request(shelter_id, item, int(qty), urgency)
            return redirect(url_for("home"))
        
    return render_template("add_request.html", shelters=shelters, items=items, error=error)
# Function for allocation of supplies for requests:
@app.route("/allocate", methods=["POST"])
def allocate():
    db.allocate_inventory()
    return redirect(url_for("home"))

# Routes for the allocation history
@app.route("/allocation_history")
def allocation_history():
    history = db.get_allocation_history()
    return render_template("allocation_history.html", history=history)


# =============================================================
#          NEW ROUTES: Hospitals, Doctors & Medic Allocation
# =============================================================

@app.route("/hospitals")
def hospitals_dashboard():
    hospitals = db.get_all_hospitals()
    doctors = db.get_all_doctors()
    return render_template("hospitals.html", hospitals=hospitals, doctors=doctors)

@app.route("/add_hospital", methods=["GET", "POST"])
def add_hospital():
    if request.method == "POST":
        hospital_id = request.form["hospital_id"]
        name = request.form["name"]
        coordinates = request.form["coordinates"]
        db.add_hospital(hospital_id, name, coordinates)
        return redirect(url_for("hospitals_dashboard"))
    return render_template("add_hospital.html")

@app.route("/add_doctor", methods=["GET", "POST"])
def add_doctor():
    hospitals = db.get_all_hospitals()
    if request.method == "POST":
        doctor_id = request.form["doctor_id"]
        hospital_id = request.form["hospital_id"]
        speciality = request.form["speciality"]
        availability_status = request.form["availability_status"]
        
        db.add_doctor(doctor_id, speciality, availability_status, hospital_id)
        return redirect(url_for("hospitals_dashboard"))
    return render_template("add_doctor.html", hospitals=hospitals)

@app.route("/add_medic_request", methods=["GET", "POST"])
def add_medic_request_route():
    error = ""
    shelters = db.get_all_shelters()
    
    if request.method == "POST":
        shelter_id = request.form["shelter_id"]
        speciality = request.form["speciality"]
        
        if not shelter_id or not speciality:
            error = "Please select both a shelter and a required medical specialty."
        else:
            # Calls your matching algorithm from db.py based on specialty and distance
            result = db.allocate_medics(shelter_id, speciality)
            if not result:
                error = f"No available doctors found with specialty '{speciality}'."
            else:
                return redirect(url_for("hospitals_dashboard"))
                
    return render_template("add_medic_request.html", shelters=shelters, error=error)


# --- MANAGER DASHBOARD ---
@app.route("/manager")
def manager_dashboard():
    master_items = db.get_all_master_items()
    master_warehouses = db.get_all_master_warehouses()
    existing_inventory = db.get_all_inventory()
    shelters = db.get_all_shelters()

    return render_template(
        "manager.html",
        items=master_items,
        warehouses=master_warehouses,
        inventory=existing_inventory,
        shelters=shelters
    )

@app.route("/manager/add_item", methods=["POST"])
def manager_add_item():
    item_name = request.form.get("item_name")
    if item_name:
        db.add_master_item(item_name)
    return redirect(url_for("manager_dashboard"))

@app.route("/manager/add_warehouse", methods=["POST"])
def manager_add_warehouse():
    warehouse_id = request.form.get("warehouse_id")
    location = request.form.get("location", "")
    if warehouse_id:
        db.add_master_warehouse(warehouse_id, location)
    return redirect(url_for("manager_dashboard"))

@app.route("/manager/edit_inventory", methods=["POST"])
def manager_edit_inventory():
    warehouse_id = request.form.get("warehouse_id")
    item = request.form.get("item")
    quantity_str = request.form.get("quantity")
    
    try:
        quantity = int(float(quantity_str))
    except (ValueError, TypeError):
        quantity = 0

    if warehouse_id and item and quantity >= 0:
        db.update_inventory_stock(warehouse_id, item, quantity)
        
    return redirect(url_for("manager_dashboard"))    

# Routes for the export functions as CSV format
@app.route("/export/csv")
def export_csv():
    requests_data = db.get_sorted_requests()
    medic_data = db.get_all_medic_requests()
    
    si = io.StringIO()
    writer = csv.writer(si)
    
    # --- Section 1: Supply Requests ---
    writer.writerow(["=== SUPPLY REQUESTS ==="])
    writer.writerow(["Request ID", "Shelter ID", "Item Required", "Requested Quantity", "Allocated Quantity", "Status", "Urgency"])
    for req in requests_data:
        writer.writerow(req)
        
    # Add spacing between sections
    writer.writerow([])
    writer.writerow([])
    
    # --- Section 2: Medical Requests ---
    writer.writerow(["=== MEDICAL / DOCTOR REQUESTS ==="])
    writer.writerow(["Request ID", "Shelter ID", "Hospital ID", "Doctor ID", "Speciality", "Status"])
    for med in medic_data:
        writer.writerow(med)
        
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=relief_system_full_report.csv"}
    )
    
if __name__ == "__main__":
    app.run(debug=True)