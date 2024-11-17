# routes.py

from flask import render_template, url_for, flash, redirect,request
from Namma_Kadai import app, db
from Namma_Kadai.models import User, Company,Item,Purchase,Sales,StoredPurchase, Cart
from werkzeug.security import generate_password_hash
from Namma_Kadai.forms import RegistrationForm,LoginForm,ItemForm,PurchaseForm,SalesForm
from flask_login import LoginManager
from werkzeug.security import check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime,timedelta
import pytz
from sqlalchemy import func
import pandas as pd
from flask import send_file
from io import BytesIO
from math import ceil
bcrypt = Bcrypt(app)


login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
login_manager.login_view = 'login'  # Replace 'login' with the actual name of your login route
login_manager.login_message = "Please log in to access this page."

#---------------------------------------------Register--------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('An account with that email already exists. Please log in or use a different email.', 'danger')
            return redirect(url_for('register'))
        user = User( email=form.email.data, password=hashed_password)
        existing_company = Company.query.filter_by(company_name=form.company_name.data).first()
        if existing_company:
            flash('A company with that name already exists. Please choose a different name.', 'danger')
            return redirect(url_for('register'))
        company = Company(company_name=form.company_name.data, user_id=user.id)  
        db.session.add(company,user)
        db.session.commit()
        flash('Your account has been created and company added!', 'success')
        return redirect(url_for('login')) 
    return render_template('register.html', title='Register', form=form)

#-----------------------------------------------Login---------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))  
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

#------------------------------------------Logout-------------------------------------------

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

#-----------------------------------------Home------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    # Get filter values from the form
    item_name_filter = request.args.get('item_name', '')
    start_rate = request.args.get('start_rate', '')
    end_rate = request.args.get('end_rate', '')
    start_qty = request.args.get('start_qty', '')
    end_qty = request.args.get('end_qty', '')

    # Start the query for items
    query = Item.query

    # Apply filters if provided
    if item_name_filter:
        query = query.filter(Item.item_name.ilike(f'%{item_name_filter}%'))
    if start_rate:
        query = query.filter(Item.rate >= float(start_rate))
    if end_rate:
        query = query.filter(Item.rate <= float(end_rate))
    if start_qty:
        query = query.filter(Item.qty >= int(start_qty))
    if end_qty:
        query = query.filter(Item.qty <= int(end_qty))

    # Set up pagination
    page = request.args.get('page', 1, type=int)
    pagination = query.paginate(page=page, per_page=5)  # Adjust `per_page` as needed
    items = pagination.items

    return render_template('home.html', items=items, pagination=pagination)

#------------------------------------------------Add New Item----------------------------------------------

@app.route('/add_item', methods=['POST'])
@login_required
def add_item():
    if request.method == 'POST':
        item_name = request.form['item_name']
        quantity = request.form['quantity'] or 0  # Default to 0 if not provided
        rate = request.form['rate']

        # Get the current user's company
        company = current_user.companies  # Assuming a one-to-one relationship with the Company model

        if company:  # Ensure the user has an associated company
            # Check if the item already exists in the current company
            existing_item = Item.query.filter_by(item_name=item_name, company_id=company.id).first()
            
            if existing_item:
                # If the item already exists, notify the user
                flash('This item already exists in your inventory!', 'warning')
                return redirect(url_for('home'))

            # Create a new Item with company_id
            new_item = Item(
                item_name=item_name,
                qty=quantity,
                rate=rate,
                company_id=company.id  # Associate the item with the company
            )

            db.session.add(new_item)
            db.session.commit()

            flash('Item added successfully!', 'success')
            return redirect(url_for('home'))  # Redirect to the home page after adding the item
        else:
            # Handle case where the user doesn't have an associated company
            flash('You must have a company to add items!', 'danger')
            return redirect(url_for('home'))

#-----------------------------------------Item Edit-------------------------------------------------------

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)  # Fetch the item or return a 404 error
    company = current_user.companies  # Assuming the user is associated with a company

    if not company:
        flash("You need to be associated with a company to edit items.", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        try:
            # Get the updated name and rate from the form
            new_name = request.form['item_name'].strip()
            new_rate = float(request.form['rate'])  # Convert input to float

            if not new_name:
                flash("Item name cannot be empty.", "warning")
                return redirect(url_for('edit_item', item_id=item_id))

            if new_rate <= 0:
                flash("Rate must be greater than zero.", "warning")
                return redirect(url_for('edit_item', item_id=item_id))

            # Check if another item with the same name already exists for the company
            existing_item = Item.query.filter(
                Item.id != item_id,  # Exclude the current item
                Item.item_name == new_name,
                Item.company_id == company.id
            ).first()

            if existing_item:
                flash("An item with this name already exists in your inventory.", "warning")
                return redirect(url_for('home', item_id=item_id))

            # Update the item's name and rate
            item.item_name = new_name
            item.rate = new_rate

            # Commit the changes to the database
            db.session.commit()

            flash('Item details updated successfully!', 'success')
            return redirect(url_for('home'))  # Redirect to the home page or relevant page

        except ValueError:
            # Handle invalid input (e.g., non-numeric rate)
            flash("Please enter a valid numeric rate.", "error")
            return redirect(url_for('edit_item', item_id=item_id))

    # Render the edit form with the current item details
    return render_template('home.html', item=item)

#--------------------------------------------------View Item-------------------------------------------------------------------

@app.route('/item/<int:item_id>')
@login_required
def view_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    # Get current page numbers for sales and purchases
    sales_page = request.args.get('sales_page', 1, type=int)
    purchases_page = request.args.get('purchases_page', 1, type=int)
    
    # Paginate sales and purchases for the item
    sales_pagination = Sales.query.filter_by(item_id=item_id).paginate(page=sales_page, per_page=5, error_out=False)
    purchases_pagination = Purchase.query.filter_by(item_id=item_id).paginate(page=purchases_page, per_page=5, error_out=False)

    return render_template(
        'view_item.html',
        item=item,
        sales_pagination=sales_pagination,
        purchases_pagination=purchases_pagination
    )

#-----------------------------------------------------Delete Item------------------------------------------------



#-----------------------------------------------------Purchase Item-------------------------------------------------

@app.route('/add_purchases', methods=['GET', 'POST'])
@login_required  # Ensures only logged-in users can access this route
def add_purchases():
    form = PurchaseForm()

    # Populate the item choices dropdown with item names
    form.item_id.choices = [(item.id, item.item_name) for item in Item.query.all()]

    if form.validate_on_submit():
        # Check if the user is logged in and associated with a company
        if current_user.is_authenticated:
            company = current_user.companies  # Assuming the User has only one Company
            if not company:  # Handle case where the user doesn't have a company
                flash('User does not have a company associated with them.', 'danger')
                return redirect(url_for('add_purchases'))

            # Retrieve the item information from the form
            item_id = form.item_id.data
            qty = form.qty.data
            rate = form.rate.data
            amount = qty * rate
            if qty <= 0:
                flash('Quantity must be positive numbers.', 'danger')
                return redirect(url_for('add_purchases'))
            if rate <= 0:
                flash('Rate must be positive numbers.', 'danger')
                return redirect(url_for('add_purchases'))

            # Check if the user's company has enough cash balance
            if company.cash_balance >= amount:
                # Check if the item already exists in StoredPurchase
                existing_purchase = StoredPurchase.query.filter_by(item_id=item_id).first()
                if existing_purchase:
                    # Update the quantity and price if the item already exists
                    existing_purchase.qty += qty
                    existing_purchase.price = rate  # Update the rate if needed
                    flash('Purchase updated successfully!', 'success')
                else:
                    # Proceed with adding the purchase if it doesn't exist
                    item = Item.query.get(item_id)  # Fetch the item to get its name
                    new_stored_purchase = StoredPurchase(
                        item_id=item.id,
                        item_name=item.item_name,
                        qty=qty,
                        price=rate
                    )
                    db.session.add(new_stored_purchase)
                    flash('Purchase added and stored successfully!', 'success')

                # Deduct the purchase amount from the company's cash balance
                company.cash_balance -= amount
                db.session.commit()  # Commit the changes to the database
                return redirect(url_for('add_purchases'))
            else:
                flash('Insufficient balance to complete this purchase.', 'danger')
        else:
            flash('You need to be logged in to add purchases.', 'warning')
    
    # Fetch all stored purchases and calculate the total amount
    items = Item.query.all()
    purchases = StoredPurchase.query.all()

    # Calculate total amount for all stored purchases
    total_amount = sum(purchase.qty * purchase.price for purchase in purchases)

    return render_template('purchase.html', form=form, purchases=purchases, items=items, total_amount=total_amount)

#---------------------------------------------Confirm Purchase Item------------------------------------------------------

@app.route('/confirm_purchases', methods=['POST'])
@login_required
def confirm_purchases():
    if not current_user.is_authenticated or not current_user.companies:
        flash("You need to be associated with a company to confirm purchases.", "error")
        return redirect(url_for('home'))
    
    # Fetch the user's company ID
    company_id = current_user.companies.id
    company = current_user.companies  # Access the company associated with the user

    # Fetch all stored purchases
    stored_purchases = StoredPurchase.query.all()
    
    for stored in stored_purchases:
        # Create a new Purchase entry for each stored purchase
        new_purchase = Purchase(
            item_id=stored.item_id,
            company_id=company_id,  # Use the associated company ID
            qty=stored.qty,
            rate=stored.price,
            amount=stored.qty * stored.price,
            timestamp=datetime.now(pytz.timezone('Asia/Kolkata'))
        )
        
        # Add and commit each purchase to the database
        db.session.add(new_purchase)
        
        # Update the Item's quantity by increasing it based on the purchase quantity
        item = Item.query.get(stored.item_id)
        if item:
            item.qty += stored.qty  # Increase the quantity of the item
        
        # Decrease the company's cash balance based on the amount of the purchase
          # Deduct the amount from cash balance
        else:
            flash("Not enough cash balance to confirm all purchases.", "error")
            db.session.rollback()  # Rollback the transaction if there's insufficient balance
            return redirect(url_for('home'))

    # Commit the changes to the database
    db.session.commit()
    
    # Optionally, delete all stored purchases after confirmation
    StoredPurchase.query.delete()
    db.session.commit()
    
    flash('Purchases confirmed, stock updated, and cash balance decreased!', 'success')
    return redirect(url_for('home'))

#-------------------------------------------Edit Confirm Purchase Item-------------------------------------------------

@app.route('/edit_purchase/<int:purchase_id>', methods=['POST'])
@login_required  # Ensure the user is logged in
def edit_purchase(purchase_id):
    # Retrieve the purchase using the provided ID
    purchase = StoredPurchase.query.get_or_404(purchase_id)
    
    # Access the user's associated company (assuming each user has one company)
    company = current_user.companies
    if not company:
        flash('User does not have a company associated with them.', 'danger')
        return redirect(url_for('add_purchases'))

    # Get the updated quantity and price from the form
    new_qty = request.form.get('qty', type=int)
    new_rate = request.form.get('rate', type=float)
    new_amount = new_qty * new_rate  # Calculate the new total cost

    # Calculate the difference in amounts
    old_amount = purchase.qty * purchase.price  # Original amount
    balance_difference = new_amount - old_amount  # Difference between old and new purchase cost

    # Check if the company has enough cash balance to cover the change
    if company.cash_balance >= balance_difference:
        # Update the purchase fields
        purchase.qty = new_qty
        purchase.price = new_rate

        # Deduct the difference from the company's cash balance
        company.cash_balance -= balance_difference

        # Commit the changes to both the purchase and the company's balance
        db.session.commit()

        flash('Purchase updated and cash balance adjusted successfully!', 'success')
    else:
        flash('Insufficient balance to update this purchase.', 'danger')

    return redirect(url_for('add_purchases'))

#-----------------------------------------------------Delete Confirm Purchase Item---------------------------------------

@app.route('/delete_purchase/<int:purchase_id>', methods=['POST'])
@login_required  # Ensure the user is logged in to delete
def delete_purchase(purchase_id):
    # Retrieve the purchase using the provided ID
    purchase = StoredPurchase.query.get_or_404(purchase_id)

    # Access the user's associated company (assuming each user has one company)
    company = current_user.companies
    if not company:
        flash('User does not have a company associated with them.', 'danger')
        return redirect(url_for('add_purchases'))

    # Calculate the amount that will be refunded to the company's cash balance
    refund_amount = purchase.qty * purchase.price

    # Increase the company's cash balance by the refund amount
    company.cash_balance += refund_amount

    # Delete the purchase record
    db.session.delete(purchase)

    # Commit the changes (both for cash balance and purchase deletion)
    db.session.commit()

    flash('Purchase deleted and cash balance restored successfully!', 'success')
    return redirect(url_for('add_purchases'))

#-----------------------------------------------View Purchase Item---------------------------------

@app.route('/purchases', methods=['GET', 'POST'])
@login_required
def purchase_list():
    # Get filters from request arguments
    item_name = request.args.get('item_name', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    page = request.args.get('page', 1, type=int)  # Get the current page number
    per_page = 5  # Number of records per page

    # Start building the query
    query = Purchase.query

    # Filter by item name
    if item_name:
        query = query.join(Item).filter(Item.item_name.ilike(f"%{item_name}%"))

    # Filter by start date
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Purchase.timestamp >= start_date_obj)
        except ValueError:
            print(f"Invalid start_date: {start_date}")

    # Filter by end date
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the end date fully
            end_date_obj += timedelta(days=1)
            query = query.filter(Purchase.timestamp < end_date_obj)
        except ValueError:
            print(f"Invalid end_date: {end_date}")

    # Get total count for pagination
    total_purchases = query.count()

    # Apply pagination
    purchases = query.order_by(Purchase.timestamp.desc()).paginate(page=page, per_page=per_page)

    # Render the template
    return render_template(
        'purchase_list.html',
        
        purchases=purchases.items,  # Only the current page's items
        total_pages=ceil(total_purchases / per_page),  # Total pages
        current_page=page,
        item_name=item_name,
        start_date=start_date,
        end_date=end_date,
    )

#---------------------------------------------------------Sale Item-----------------------------------

@app.route('/add_sale', methods=['GET', 'POST'])
@login_required
def add_sale():
    form = SalesForm()

    # Calculate the total price for all sales
    sales = StoredPurchase.query.all()
    total_price = sum(sale.qty * sale.price for sale in sales)

    # Populate the item choices dropdown with item names and IDs
    form.item_id.choices = [(item.id, item.item_name) for item in Item.query.all()]

    if form.validate_on_submit():
        if current_user.is_authenticated:
            # Get form data
            item_id = form.item_id.data
            qty = form.qty.data

            # Fetch the item to access current rate and stock
            item = Item.query.get(item_id)
            if item is None:
                flash('Selected item does not exist.', 'danger')
                return redirect(url_for('add_sale'))

            rate = item.rate
            amount = qty * rate

            # Check if there is enough stock to fulfill the sale
            if qty <= item.qty:
                # Check if the sale record for the selected item already exists
                existing_sale = StoredPurchase.query.filter_by(item_id=item.id).first()
                if existing_sale:
                    # Update the existing sale record
                    existing_sale.qty += qty
                    existing_sale.price = rate  # Optionally, update the price if needed
                else:
                    # Create new sale record
                    new_sale = StoredPurchase(
                        item_id=item.id,
                        item_name=item.item_name,
                        qty=qty,
                        price=rate
                    )
                    db.session.add(new_sale)

                # Update the item quantity
                item.qty -= qty

                # Commit the transaction
                db.session.commit()

                flash('Sale added successfully!', 'success')
                return redirect(url_for('add_sale'))
            else:
                flash('Insufficient stock for this sale.', 'danger')
        else:
            flash('You need to be logged in to add sales.', 'warning')

    # Pagination for sales
    page = request.args.get('page', 1, type=int)  # Get the page number from the query string, default to 1
    pagination = StoredPurchase.query.paginate(page=page, per_page=5)  # Adjust `per_page` as needed
    sales = pagination.items

    return render_template('sale.html', form=form, sales=sales, items=Item.query.all(), pagination=pagination, total_price=total_price)



@app.route('/confirm_sale', methods=['POST'])
@login_required
def confirm_sale():                    
    if not current_user.is_authenticated or not current_user.companies:
        flash("You need to be associated with a company to confirm sales.", "error")
        return redirect(url_for('home'))
    
    # Fetch the user's company ID
    company_id = current_user.companies.id
    company = current_user.companies  # Access the company associated with the user

    # Fetch all stored purchases (sales)
    stored_sales = StoredPurchase.query.all()
    
    for stored in stored_sales:
        # Create a new Sale entry for each stored sale
        new_sale = Sales(
            item_id=stored.item_id,
            company_id=company_id,  # Use the associated company ID
            qty=stored.qty,
            rate=stored.price,
            amount=stored.qty * stored.price,
            timestamp=datetime.now(pytz.timezone('Asia/Kolkata'))
        )
        
        # Add and commit each sale to the database
        db.session.add(new_sale)
        
        # Update the Item's quantity by decreasing it based on the sale quantity
        item = Item.query.get(stored.item_id)
          # Decrease the quantity of the item
        if item.qty <= 10:
                existing_cart = Cart.query.filter_by(item_id=item.id, company_id=company_id).first()
                
                # If item is not already in the cart, add it with available_qty and purchase_qty
                if not existing_cart:
                    new_cart_entry = Cart(
                        item_id=item.id,
                        company_id=company_id,
                        available_qty=item.qty,
                        purchase_qty=0,  # This can be adjusted as needed
                        product_name=item.item_name
                    )
                    db.session.add(new_cart_entry)
        else:
            flash("Not enough stock to complete the sale.", "error")
            db.session.rollback()  # Rollback the transaction if there's insufficient stock
            return redirect(url_for('home'))
        
        # Increase the company's cash balance based on the sale amount
        company.cash_balance += new_sale.amount

    # Commit the changes to the database
    db.session.commit()
    
    # Optionally, delete all stored sales after confirmation
    StoredPurchase.query.delete()
    db.session.commit()
    
    flash('Sales confirmed, stock updated, and cash balance increased!', 'success')
    return redirect(url_for('home'))



@app.route('/edit_sale/<int:sale_id>', methods=['POST'])
@login_required
def edit_sale(sale_id):
    sale = StoredPurchase.query.get_or_404(sale_id)

    # Debug: Check the sale item ID
   

    # Try to retrieve the item using the sale's item_id
    item = Item.query.get(sale.item_id)

    if not item:  # Check if the item exists
        flash(f"Item with ID {sale.item_id} not found. Please check the item ID.", 'error')
        # Log the error to a file or console
        app.logger.error(f"Item with ID {sale.item_id} not found for sale ID {sale.id}")
        return redirect(url_for('add_sale'))

    # Get the new quantity and rate from the form
    try:
        new_qty = int(request.form['qty'])
        new_rate = float(request.form['rate'])
    except ValueError:
        flash('Invalid input for quantity or rate. Please enter valid numbers.', 'error')
        return redirect(url_for('add_sale'))

    # Check if the new quantity does not exceed the available stock
    if new_qty <= item.qty:  # Ensure new qty does not exceed available stock
        # Calculate the difference between the current sale quantity and the new quantity
        qty_difference = new_qty - sale.qty

        # Update the item qty based on the difference in quantities
        item.qty -= qty_difference  # Adjust the stock by the difference in quantity

        # Update the sale record with the new quantity and rate
        sale.qty = new_qty
        sale.rate = new_rate
        sale.amount = new_qty * new_rate  # Update the amount based on the new quantity and rate

        try:
            db.session.commit()  # Commit the changes to the database
            flash('Sale quantity updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()  # Rollback if there is any error
            flash(f"An error occurred while updating the sale: {str(e)}", 'error')
    else:
        flash('Quantity exceeds available stock. Please reduce the quantity.', 'error')

    return redirect(url_for('add_sale'))



@app.route('/delete_sale/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def delete_sale(sale_id):
    purchase = StoredPurchase.query.get_or_404(sale_id)
    
    # Get the item associated with the sale
    item = Item.query.get(purchase.item_id)
    
    if item:
        # Increase the item's quantity by the quantity sold in the deleted sale
        item.qty += purchase.qty
        db.session.commit()
    
    # Delete the sale record from StoredPurchase
    db.session.delete(purchase)
    db.session.commit()

    flash('Purchase deleted and item quantity restored successfully!', 'success')
    return redirect(url_for('add_sale'))



@app.route('/sale',methods=['GET','POST'])
@login_required
def sale_list():
    sales = Sales.query.all()
    return render_template('sale_list.html', sales=sales)
from flask import jsonify, request

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
# Other imports


















































@app.route('/item/<int:item_id>/purchase', methods=['GET', 'POST'])
@login_required
def purchase_item(item_id):
    company_id = current_user.companies
    item = Item.query.get_or_404(item_id)
    
    if request.method == 'POST':
        qty = int(request.form['qty'])
        purchase_price = float(request.form['purchase_price'])  # purchase_price is used as rate
        
        # Ensure the purchase price is not negative or zero
        if purchase_price <= 0:
            flash('Purchase price must be greater than zero.', 'danger')
            return redirect(url_for('view_item', item_id=item.id))
        
        # Calculate the total purchase amount
        total_amount = purchase_price * qty

        # Add the purchase record
        purchase = Purchase(item_id=item.id, qty=qty, amount=total_amount, rate=purchase_price,company_id=company_id)

        db.session.add(purchase)
        db.session.commit()

        # Update item quantity
        item.qty += qty
        db.session.commit()

        flash(f'Successfully purchased {qty} of {item.item_name}.', 'success')
        return redirect(url_for('view_item', item_id=item.id))

    return render_template('view_item.html', item=item)



@app.route('/cart')
@login_required
def cart():
    # Ensure the user has an associated company
    if not current_user.companies:
        flash("You need to be associated with a company to view the cart.", "error")
        return redirect(url_for('home'))

    # Fetch all cart items for the current user's company
    cart_items = Cart.query.filter_by(company_id=current_user.companies.id).all()
    return render_template('cart.html', cart_items=cart_items)


@app.route('/update_cart_quantities', methods=['POST'])
@login_required
def update_cart_quantities():
    company = Company.query.filter_by(user_id=current_user.id).first()
    
    # Ensure the user has an associated company
    if not current_user.companies:
        flash("You need to be associated with a company to confirm purchases.", "error")
        return redirect(url_for('cart'))
    
    
    

    # Retrieve and update quantities for each item in the cart
    for cart_item in Cart.query.filter_by(company_id=current_user.companies.id).all():
        
        new_qty = request.form.get(f'purchase_qty_{cart_item.item_id}', type=int)
        if new_qty and new_qty > 0:
            cart_item.purchase_qty = new_qty
            item = Item.query.get(cart_item.item_id)
            if item:
                # Adjust the item's quantity in stock
                if new_qty>=1:
                    # Deduct the new purchase quantity
                    cash_sum = (new_qty * item.rate)
                    if cash_sum > company.cash_balance:
                        flash(f"Cannot purchase {item.item_name} due to insufficient balance.", "danger")
                        continue
                    else:
                        item.qty += new_qty 
                        company.cash_balance -= cash_sum
                        new_purchase = Purchase(
                        item_id=cart_item.item_id,
                        company_id=cart_item.company_id,  # Use the associated company ID
                        qty=cart_item.available_qty,
                        rate=item.rate,
                        amount=cash_sum,
                        timestamp=datetime.now(pytz.timezone('Asia/Kolkata'))
                    )
                        db.session.add(new_purchase)
                        db.session.delete(cart_item)
                        db.session.add(item)

        else:
            flash(f"Invalid quantity for {cart_item.item.name}.", "error")
    
    
    
    db.session.commit()
    flash('Cart quantities updated and items purchased!', 'success')
    return redirect(url_for('cart'))



@app.route('/inventory_report', methods=['GET', 'POST'])
@login_required
def inventory_report():
    # Get the filter value from the request (if any)
    filter_name = request.args.get('item_name', '')

    # Query for report data with an optional filter on item_name
    query = db.session.query(
        Item.item_name.label("item_name"),
        Item.qty.label("available_qty"),
        func.coalesce(func.sum(Purchase.qty), 0).label("total_purchased"),
        func.coalesce(func.sum(Sales.qty), 0).label("total_sold")
    ).outerjoin(Purchase, Purchase.item_id == Item.id) \
     .outerjoin(Sales, Sales.item_id == Item.id) \
     .group_by(Item.id)

    if filter_name:
        query = query.filter(Item.item_name.ilike(f"%{filter_name}%"))

    report_data = query.all()

    # Calculate total available, purchased, and sold counts
    total_available = sum([item.available_qty for item in report_data])
    total_purchased = sum([item.total_purchased for item in report_data])
    total_sold = sum([item.total_sold for item in report_data])

    # Pass data to the template
    return render_template('inventory_report.html', 
                           report_data=report_data, 
                           total_available=total_available,
                           total_purchased=total_purchased,
                           total_sold=total_sold,
                           filter_name=filter_name)



@app.route('/export_excel')
def export_excel():
    # Get all items from your Item model
    items = Item.query.all()

    # Create a list of dictionaries to pass to pandas DataFrame
    data = []
    for item in items:
        data.append({
            'ID': item.id,
            'Item Name': item.item_name,
            'Quantity': item.qty,
            'Rate': item.rate,
            'Company ID': item.company_id
        })

    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(data)

    # Save to a BytesIO buffer (so it can be sent directly to the client)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Items')
    output.seek(0)  # Rewind the buffer to the beginning

    # Send the file as a response
    return send_file(output, as_attachment=True, download_name='items_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/export_purchases_excel')
def export_purchases_excel():
    # Get all purchases from your Purchase model
    purchases = Purchase.query.all()

    # Create a list of dictionaries to pass to pandas DataFrame
    data = []
    for purchase in purchases:
        data.append({
            'ID': purchase.id,
            'Item ID': purchase.item_id,
            'Company ID': purchase.company_id,
            'Quantity': purchase.qty,
            'Rate': purchase.rate,
            'Amount': purchase.amount,
            'Timestamp': purchase.timestamp
        })

    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(data)

    # Save to a BytesIO buffer (so it can be sent directly to the client)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Purchases')
    output.seek(0)  # Rewind the buffer to the beginning

    # Send the file as a response
    return send_file(output, as_attachment=True, download_name='purchases_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')



@app.route('/export_sales_excel')
def export_sales_excel():
    # Get all sales from your Sales model
    sales = Sales.query.all()

    # Create a list of dictionaries to pass to pandas DataFrame
    data = []
    for sale in sales:
        data.append({
            'ID': sale.id,
            'Item ID': sale.item_id,
            'Company ID': sale.company_id,
            'Quantity': sale.qty,
            'Rate': sale.rate,
            'Amount': sale.amount,
            'Timestamp': sale.timestamp
        })

    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(data)

    # Save to a BytesIO buffer (so it can be sent directly to the client)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales')
    output.seek(0)  # Rewind the buffer to the beginning

    # Send the file as a response
    return send_file(output, as_attachment=True, download_name='sales_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
