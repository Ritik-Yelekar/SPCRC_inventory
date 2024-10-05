from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from io import StringIO
import csv
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

# Filepath for the usage log CSV file
USAGE_LOG_CSV = 'usage_history.csv'

# Database Models
class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    restock_threshold = db.Column(db.Integer, default=10)

class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'))
    user_name = db.Column(db.String(100))
    quantity_taken = db.Column(db.Integer)
    date_taken = db.Column(db.DateTime, default=datetime.utcnow)  # Stores the time the item was taken
    item = db.relationship('InventoryItem', backref='usage_logs')

# Route for the main index page
@app.route('/')
def index():
    items = InventoryItem.query.all()
    search = request.args.get('search')
    if search:
        items = InventoryItem.query.filter(InventoryItem.name.like(f'%{search}%')).all()
    return render_template('index.html', items=items)

# Add item
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        restock_threshold = request.form['restock_threshold']
        new_item = InventoryItem(name=name, quantity=int(quantity), restock_threshold=int(restock_threshold))
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!')
        return redirect(url_for('index'))
    return render_template('add_item.html')

# Update item
@app.route('/update_item/<int:id>', methods=['GET', 'POST'])
def update_item(id):
    item = InventoryItem.query.get_or_404(id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.quantity = request.form['quantity']
        item.restock_threshold = request.form['restock_threshold']
        db.session.commit()
        flash('Item updated successfully!')
        return redirect(url_for('index'))
    return render_template('update_item.html', item=item)

# Log usage and update CSV
@app.route('/usage_log', methods=['GET', 'POST'])
def usage_log():
    if request.method == 'POST':
        item_id = request.form['item_id']
        user_name = request.form['user_name']
        quantity_taken = request.form['quantity']
        item = InventoryItem.query.get(item_id)
        if item and item.quantity >= int(quantity_taken):
            item.quantity -= int(quantity_taken)
            new_log = UsageLog(item_id=item_id, user_name=user_name, quantity_taken=int(quantity_taken))
            db.session.add(new_log)
            db.session.commit()
            flash('Usage recorded successfully!')
            
            # Update the usage history CSV
            append_usage_log_to_csv(new_log)
        else:
            flash('Insufficient quantity!')
        return redirect(url_for('usage_log'))
    
    items = InventoryItem.query.all()
    logs = UsageLog.query.order_by(UsageLog.date_taken.desc()).all()  # Fetch all logs ordered by time
    return render_template('usage_log.html', items=items, logs=logs)

# Helper function to append usage log to CSV file
def append_usage_log_to_csv(log):
    """Appends a new usage log entry to the CSV file."""
    file_exists = os.path.isfile(USAGE_LOG_CSV)
    
    with open(USAGE_LOG_CSV, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        if not file_exists:
            # Write the header if the file doesn't exist
            writer.writerow(['Item Name', 'User Name', 'Quantity Taken', 'Date & Time Taken'])
        
        # Write the log data to the CSV
        writer.writerow([log.item.name, log.user_name, log.quantity_taken, log.date_taken.strftime('%Y-%m-%d %H:%M:%S')])

# Download CSV with usage history
@app.route('/download_usage_csv')
def download_usage_csv():
    """Download the usage history CSV."""
    if os.path.exists(USAGE_LOG_CSV):
        return send_file(USAGE_LOG_CSV, mimetype='text/csv', as_attachment=True, attachment_filename="usage_history.csv")
    else:
        flash("Usage log CSV not found.")
        return redirect(url_for('usage_log'))

# Delete item
@app.route('/delete_item/<int:id>')
def delete_item(id):
    item = InventoryItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash(f'Item {item.name} has been deleted successfully!')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
