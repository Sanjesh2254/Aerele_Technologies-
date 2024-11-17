# routes.py

from flask import render_template, url_for, flash, redirect,request
from Namma_Kadai import app, db
from Namma_Kadai.models import User, Company,Item,Purchase,Sales,StoredPurchase, Cart,Storedsale
from werkzeug.security import generate_password_hash
from Namma_Kadai.forms import RegistrationForm,LoginForm,PurchaseForm,SalesForm
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
        db.session.add(user)
        db.session.commit()
        existing_company = Company.query.filter_by(company_name=form.company_name.data).first()
        if existing_company:
            flash('A company with that name already exists. Please choose a different name.', 'danger')
            return redirect(url_for('register'))
        company = Company(company_name=form.company_name.data, user_id=user.id)  
        db.session.add(company)
        db.session.commit()
        flash('Your account has been created and company added!', 'success')
        return redirect(url_for('home')) 
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
            return redirect(url_for('add_sale'))  
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
    item_name_filter = request.args.get('item_name', '')
    start_rate = request.args.get('start_rate', '')
    end_rate = request.args.get('end_rate', '')
    start_qty = request.args.get('start_qty', '')
    end_qty = request.args.get('end_qty', '')
    company_id = current_user.companies.id  
    query = Item.query.filter_by(company_id=company_id)
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
    page = request.args.get('page', 1, type=int)
    pagination = query.paginate(page=page, per_page=5)  
    items = pagination.items
    return render_template('home.html', items=items, pagination=pagination)

#------------------------------------------------Add New Item----------------------------------------------

@app.route('/add_item', methods=['POST'])
@login_required
def add_item():
    if request.method == 'POST':
        item_name = request.form['item_name']
        quantity = request.form['quantity'] or 0  #
        rate = request.form['rate']
        if int(rate)<=0:
                flash('Enter rate must be positive numbers, try again.', 'danger')
                return redirect(url_for('home'))
        company = current_user.companies  
        if company:  
            existing_item = Item.query.filter_by(item_name=item_name, company_id=company.id).first()
            if existing_item:
                flash('This item already exists in your inventory!', 'warning')
                return redirect(url_for('home'))
            new_item = Item(
                item_name=item_name,
                qty=quantity,
                rate=rate,
                company_id=company.id 
            )
            db.session.add(new_item)
            db.session.commit()
            flash('Item added successfully!', 'success')
            return redirect(url_for('home'))  
        else:
            flash('You must have a company to add items!', 'danger')
            return redirect(url_for('home'))

#-----------------------------------------Item Edit-------------------------------------------------------

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)  
    company = current_user.companies  
    if not company:
        flash("You need to be associated with a company to edit items.", "error")
        return redirect(url_for('home'))
    if request.method == 'POST':
        try:
            new_name = request.form['item_name'].strip()
            new_rate = float(request.form['rate'])  
            if not new_name:
                flash("Item name cannot be empty.", "warning")
                return redirect(url_for('edit_item', item_id=item_id))
            if new_rate <= 0:
                flash("Rate must be greater than zero.", "warning")
                return redirect(url_for('edit_item', item_id=item_id))
            existing_item = Item.query.filter(
                Item.id != item_id,  
                Item.item_name == new_name,
                Item.company_id == company.id ).first()
            if existing_item:
                flash("An item with this name already exists in your inventory.", "warning")
                return redirect(url_for('home', item_id=item_id))
            item.item_name = new_name
            item.rate = new_rate
            db.session.commit()
            flash('Item details updated successfully!', 'success')
            return redirect(url_for('home'))  
        except ValueError:
            flash("Please enter a valid numeric rate.", "error")
            return redirect(url_for('edit_item', item_id=item_id))
    return render_template('home.html', item=item)

#--------------------------------------------------View Item Detail-------------------------------------------------------------------

@app.route('/item/<int:item_id>')
def view_item(item_id):
    item = Item.query.get_or_404(item_id)
    sales_page = request.args.get('sales_page', 1, type=int)
    sales_per_page = 5 
    sales = Sales.query.filter_by(item_id=item_id).paginate(page=sales_page, per_page=sales_per_page)
    purchases_page = request.args.get('purchases_page', 1, type=int)
    purchases_per_page = 5  
    purchases = Purchase.query.filter_by(item_id=item_id).paginate(page=purchases_page, per_page=purchases_per_page)
    return render_template(
        'view_item.html',
        item=item,
        sales_pagination=sales,
        purchases_pagination=purchases
    )


#-----------------------------------------------------Purchase Item-------------------------------------------------

@app.route('/add_purchases', methods=['GET', 'POST'])
@login_required  
def add_purchases():
    form = PurchaseForm()
    form.item_id.choices = [(item.id, item.item_name) for item in Item.query.all()]
    if form.validate_on_submit():
        if current_user.is_authenticated:
            company = current_user.companies  
            if not company:  
                flash('User does not have a company associated with them.', 'danger')
                return redirect(url_for('add_purchases'))
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
            if company.cash_balance >= amount:
                existing_purchase = StoredPurchase.query.filter_by(item_id=item_id).first()
                if existing_purchase:
                    existing_purchase.qty += qty
                    existing_purchase.price = rate  
                    flash('Purchase updated successfully!', 'success')
                else:
                    item = Item.query.get(item_id)  
                    new_stored_purchase = StoredPurchase(
                        item_id=item.id,
                        item_name=item.item_name,
                        qty=qty,
                        price=rate
                    )
                    db.session.add(new_stored_purchase)
                    flash('Purchase added and stored successfully!', 'success')
                company.cash_balance -= amount
                db.session.commit() 
                return redirect(url_for('add_purchases'))
            else:
                flash('Insufficient balance to complete this purchase.', 'danger')
        else:
            flash('You need to be logged in to add purchases.', 'warning')
    company_id = current_user.companies.id
    items = Item.query.filter_by(company_id=company_id).all()
    purchases = StoredPurchase.query.all()
    total_amount = sum(purchase.qty * purchase.price for purchase in purchases)
    return render_template('purchase.html', form=form, purchases=purchases, items=items, total_amount=total_amount)

#---------------------------------------------Confirm Purchase Item------------------------------------------------------

@app.route('/confirm_purchases', methods=['POST'])
@login_required
def confirm_purchases():
    if not current_user.is_authenticated or not current_user.companies:
        flash("You need to be associated with a company to confirm purchases.", "error")
        return redirect(url_for('home'))
    company_id = current_user.companies.id
    company = current_user.companies 
    stored_purchases = StoredPurchase.query.all()
    for stored in stored_purchases:
        new_purchase = Purchase(
            item_id=stored.item_id,
            company_id=company_id,
            qty=stored.qty,
            rate=stored.price,
            amount=stored.qty * stored.price,
            timestamp=datetime.now(pytz.timezone('Asia/Kolkata'))
        )
        db.session.add(new_purchase)
        item = Item.query.get(stored.item_id)
        if item:
            item.qty += stored.qty  
        else:
            flash("Not enough cash balance to confirm all purchases.", "error")
            db.session.rollback()  
            return redirect(url_for('home'))
    db.session.commit()
    StoredPurchase.query.delete()
    db.session.commit()
    flash('Purchases confirmed, stock updated, and cash balance decreased!', 'success')
    return redirect(url_for('home'))

#-------------------------------------------Edit Confirm Purchase Item-------------------------------------------------

@app.route('/edit_purchase/<int:purchase_id>', methods=['POST'])
@login_required  
def edit_purchase(purchase_id):
    purchase = StoredPurchase.query.get_or_404(purchase_id)
    company = current_user.companies
    if not company:
        flash('User does not have a company associated with them.', 'danger')
        return redirect(url_for('add_purchases'))
    new_qty = request.form.get('qty', type=int)
    new_rate = request.form.get('rate', type=float)
    new_amount = new_qty * new_rate 
    old_amount = purchase.qty * purchase.price  
    balance_difference = new_amount - old_amount  
    if company.cash_balance >= balance_difference:
        purchase.qty = new_qty
        purchase.price = new_rate
        company.cash_balance -= balance_difference
        db.session.add(purchase)
        db.session.commit()
        flash('Purchase updated and cash balance adjusted successfully!', 'success')
    else:
        flash('Insufficient balance to update this purchase.', 'danger')
    return redirect(url_for('add_purchases'))

#-----------------------------------------------------Delete Confirm Purchase Item---------------------------------------

@app.route('/delete_purchase/<int:purchase_id>', methods=['POST'])
@login_required  
def delete_purchase(purchase_id):
    purchase = StoredPurchase.query.get_or_404(purchase_id)
    company = current_user.companies
    if not company:
        flash('User does not have a company associated with them.', 'danger')
        return redirect(url_for('add_purchases'))
    refund_amount = purchase.qty * purchase.price
    company.cash_balance += refund_amount
    db.session.delete(purchase)
    db.session.commit()
    flash('Purchase deleted and cash balance restored successfully!', 'success')
    return redirect(url_for('add_purchases'))

#-----------------------------------------------View Purchase Item---------------------------------

@app.route('/purchases', methods=['GET', 'POST'])
@login_required
def purchase_list():
    item_name = request.args.get('item_name', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    page = request.args.get('page', 1, type=int)  
    per_page = 5  
    company_id = current_user.companies.id  
    query = Purchase.query.filter_by(company_id=company_id)
    if item_name:
        query = query.join(Item).filter(Item.item_name.ilike(f"%{item_name}%"))
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Purchase.timestamp >= start_date_obj)
        except ValueError:
            print(f"Invalid start_date: {start_date}")
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            end_date_obj += timedelta(days=1)
            query = query.filter(Purchase.timestamp < end_date_obj)
        except ValueError:
            print(f"Invalid end_date: {end_date}")
    total_purchases = query.count()
    purchases = query.order_by(Purchase.timestamp.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'purchase_list.html',
        purchases=purchases.items, 
        total_pages=ceil(total_purchases / per_page), 
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
            company = current_user.companies  
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
                existing_sale = Storedsale.query.filter_by(item_id=item.id).first()
                if existing_sale:
                    # Update the existing sale record
                    existing_sale.qty += qty
                    existing_sale.price = rate  # Optionally, update the price if needed
                else:
                    # Create new sale record
                    new_sale = Storedsale(
                        item_id=item.id,
                        item_name=item.item_name,
                        qty=qty,
                        price=rate
                    )
                    db.session.add(new_sale)

                # Update the item quantity
                item.qty -= qty
                company.cash_balance += amount

                # Commit the transaction
                db.session.commit()

                flash('Sale added successfully!', 'success')
                return redirect(url_for('add_sale'))
            else:
                flash('Insufficient stock for this sale.', 'danger')
        else:
            flash('You need to be logged in to add sales.', 'warning')

    company_id = current_user.companies.id
    items= Item.query.filter_by(company_id=company_id).all()

    # Pagination for sales
    page = request.args.get('page', 1, type=int)  # Get the page number from the query string, default to 1
    pagination = Storedsale.query.paginate(page=page, per_page=5)  # Adjust per_page as needed
    sales = pagination.items
    

    return render_template('sale.html', form=form, sales=sales, items=items, pagination=pagination, total_price=total_price)



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
    stored_sales = Storedsale.query.all()
    
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
        

    # Commit the changes to the database
    db.session.commit()
    
    # Optionally, delete all stored sales after confirmation
    Storedsale.query.delete()
    db.session.commit()
    
    flash('Sales confirmed, stock updated, and cash balance increased!', 'success')
    return redirect(url_for('home'))

#------------------------------------------------------Edit Confirm Sale Item--------------------------------------------------

@app.route('/edit_sale/<int:sale_id>', methods=['POST'])
@login_required
def edit_sale(sale_id):
    company = current_user.companies 
    sale = Storedsale.query.get_or_404(sale_id)
    item = Item.query.get(sale.item_id)
    if not item: 
        flash(f"Item with ID {sale.item_id} not found. Please check the item ID.", 'error')
        app.logger.error(f"Item with ID {sale.item_id} not found for sale ID {sale.id}")
        return redirect(url_for('add_sale'))
    try:
        new_qty = int(request.form['qty'])
        new_rate = float(request.form['rate'])
    except ValueError:
        flash('Invalid input for quantity or rate. Please enter valid numbers.', 'error')
        return redirect(url_for('add_sale'))
    if new_qty <= item.qty:  
        qty_difference = new_qty - sale.qty
        item.qty -= qty_difference 
        sale.qty = new_qty
        sale.rate = new_rate
        sale.amount = new_qty * new_rate  
        company.cash_balance += qty_difference * sale.rate
        try:
            db.session.commit()  
            flash('Sale quantity updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()  
            flash(f"An error occurred while updating the sale: {str(e)}", 'error')
    else:
        flash('Quantity exceeds available stock. Please reduce the quantity.', 'error')
    return redirect(url_for('add_sale'))

#---------------------------------------------------DElete Confirm Sale Item------------------------------------------------

@app.route('/delete_sale/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def delete_sale(sale_id):
    company = current_user.companies 
    sale = Storedsale.query.get_or_404(sale_id)
    item = Item.query.get(sale.item_id)
    if item:
        item.qty += sale.qty
        company.cash_balance -= sale.qty * item.rate
        db.session.commit()
    db.session.delete(sale)
    db.session.commit()
    flash('Purchase deleted and item quantity restored successfully!', 'success')
    return redirect(url_for('add_sale'))

#-----------------------------------------------View Sale Item-------------------------------------------------------------------

@app.route('/sale',methods=['GET','POST'])
@login_required
def sale_list():
    company_id = current_user.companies.id 
    sales = Sales.query.filter_by(company_id=company_id).all()
    return render_template('sale_list.html', sales=sales)

#------------------------------------------------ view if item reduce 10 to item add the cart ---------------------------------------------

@app.route('/cart')
@login_required
def cart():
    if not current_user.companies:
        flash("You need to be associated with a company to view the cart.", "error")
        return redirect(url_for('home'))
    cart_items = Cart.query.filter_by(company_id=current_user.companies.id).all()
    return render_template('cart.html', cart_items=cart_items)

#--------------------------------------update cart----------------------------------------------------------

@app.route('/update_cart_quantities', methods=['POST'])
@login_required
def update_cart_quantities():
    company = Company.query.filter_by(user_id=current_user.id).first()
    if not current_user.companies:
        flash("You need to be associated with a company to confirm purchases.", "error")
        return redirect(url_for('cart'))
    for cart_item in Cart.query.filter_by(company_id=current_user.companies.id).all():   
        new_qty = request.form.get(f'purchase_qty_{cart_item.item_id}', type=int)
        if new_qty and new_qty > 0:
            cart_item.purchase_qty = new_qty
            item = Item.query.get(cart_item.item_id)
            if item:
                if new_qty>=1:
                    cash_sum = (new_qty * item.rate)
                    if cash_sum > company.cash_balance:
                        flash(f"Cannot purchase {item.item_name} due to insufficient balance.", "danger")
                        continue
                    else:
                        item.qty += new_qty 
                        company.cash_balance -= cash_sum
                        new_purchase = Purchase(
                        item_id=cart_item.item_id,
                        company_id=cart_item.company_id,  
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

#---------------------------------------------------------------------Report----------------------------

@app.route('/inventory_report', methods=['GET', 'POST'])
@login_required
def inventory_report():
    filter_name = request.args.get('filter_name', '').strip()
    items_query = db.session.query(Item)
    if filter_name:
        items_query = items_query.filter(Item.item_name.ilike(f"%{filter_name}%"))
    items = items_query.all()
    report_data = []
    for item in items:
        total_purchased = db.session.query(db.func.sum(Purchase.qty)).filter(Purchase.item_id == item.id).scalar() or 0
        total_sold = db.session.query(db.func.sum(Sales.qty)).filter(Sales.item_id == item.id).scalar() or 0
        total_available = total_purchased - total_sold
        report_data.append({
            'item_name': item.item_name,
            'total_purchased': total_purchased,
            'total_sold': total_sold,
            'total_available': total_available
        })
    total_available = sum([data['total_available'] for data in report_data])
    total_purchased = sum([data['total_purchased'] for data in report_data])
    total_sold = sum([data['total_sold'] for data in report_data])
    return render_template('inventory_report.html',
                           report_data=report_data,
                           total_available=total_available,
                           total_purchased=total_purchased,
                           total_sold=total_sold,
                           filter_name=filter_name)

#--------------------------------------------Export item report---------------------------------------------------

@app.route('/export_excel')
def export_excel():
    company_id = current_user.companies.id  
    items = Item.query.filter_by(company_id=company_id).all()
    data = []
    for item in items:
        data.append({
            'ID': item.id,
            'Item Name': item.item_name,
            'Quantity': item.qty,
            'Rate': item.rate,
            'Company ID': item.company_id
        })
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Items')
    output.seek(0) 
    return send_file(output, as_attachment=True, download_name='items_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

#-----------------------------------------------------Export purchases report--------------------------------

@app.route('/export_purchases_excel')
def export_purchases_excel():
    company_id = current_user.companies.id  
    purchases = Purchase.query.filter_by(company_id=company_id).all()
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
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Purchases')
    output.seek(0) 
    return send_file(output, as_attachment=True, download_name='purchases_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

#--------------------------------------------------------------Export sale report---------------------------------------------------------------------

@app.route('/export_sales_excel')
def export_sales_excel():
    company_id = current_user.companies.id
    sales = Sales.query.filter_by(company_id=company_id).all()
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
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales')
    output.seek(0) 
    return send_file(output, as_attachment=True, download_name='sales_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')