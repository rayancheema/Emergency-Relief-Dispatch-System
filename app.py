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
        search=search
    )
        
# Route to add stock supplies to a warehouse.
@app.route("/add_inventory", methods=["GET", "POST"])
def add_inventory():
    error = ""
    if request.method == "POST":
        warehouse_id = request.form["warehouse_id"]
        item = request.form["item"]
        quantity = request.form["quantity"]
        if not warehouse_id or not item or int(quantity) <0:
            error = "Please enter valid warehouse stock values (quantity cannot be negative)."
        else: 
            quantity = int(quantity)
            db.add_inventory_item(warehouse_id, item, quantity)
            return redirect(url_for("home"))
    return render_template("add_inventory.html",error = error)

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
    error= ""
    shelters = db.get_all_shelters()

    if request.method == "POST":
        shelter_id = request.form["shelter_id"]
        item = request.form["item"]
        qty = request.form["qty"]
        urgency = request.form["urgency"]
        
        if not shelter_id or not item or not qty or int(qty) <= 0:
            error = "Please fill out all request fields correctly."
        else:
            db.add_request(shelter_id, item, int(qty), urgency)
            return redirect(url_for("home"))
        
    return render_template("add_request.html", shelters=shelters, error=error)

# Function for allocation of supplies for requests:
@app.route("/allocate", methods=["POST"])
def allocate():
    db.allocate_inventory()
    return redirect(url_for("home"))


# Routes for the export functions as CSV format

@app.route("/export/csv")
def export_csv():
    requests_data = db.get_sorted_requests()
    
    si = io.StringIO()
    writer = csv.writer(si)
    # Header row
    writer.writerow(["Request ID","Shelter ID","Item Required","Requested Quantity","Allocated Quantity","Status","Urgency"])
    
    # Data rows
    for req in requests_data:
        writer.writerow(req)
        
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=shelter_requests_report.csv"}
    )


if __name__ == "__main__":
    app.run(debug=True)