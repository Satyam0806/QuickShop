from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Product, Cart, Order, OrderItem
from forms import LoginForm, ProductForm, UpdateOrderForm
from forms import LoginForm, ProductForm, UpdateOrderForm, RegistrationForm
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CheckoutForm

routes = Blueprint('routes', __name__)

# Home page route
@routes.route('/')
def home():
    products = Product.query.all()
    recommended_products = []
    
    # If user is logged in, provide personalized recommendations
    if current_user.is_authenticated and not current_user.is_admin and not current_user.is_delivery_partner:
        # Get product recommendations based on gender if available
        if current_user.gender:
            if current_user.gender == 'male':
                recommended_products = Product.query.filter(
                    (Product.name.ilike('%men%')) | 
                    (Product.description.ilike('%men%'))
                ).limit(4).all()
            elif current_user.gender == 'female':
                recommended_products = Product.query.filter(
                    (Product.name.ilike('%women%')) | 
                    (Product.description.ilike('%women%'))
                ).limit(4).all()
        
        # If no gender-specific recommendations or not enough, add random products
        if len(recommended_products) < 4:
            # Get random products to fill up to 4 recommendations
            existing_ids = [p.id for p in recommended_products]
            additional_products = Product.query.filter(~Product.id.in_(existing_ids)).order_by(db.func.random()).limit(4-len(recommended_products)).all()
            recommended_products.extend(additional_products)
    
    return render_template('home.html', products=products, recommended_products=recommended_products)

# Delivery Partner dashboard
@routes.route('/delivery')
@login_required
def delivery_dashboard():
    if not current_user.is_delivery_partner:
        abort(403)
    
    # Get orders that have been claimed by admins (have assigned_admin_id)
    orders = Order.query.filter(Order.assigned_admin_id.isnot(None)).all()
    
    return render_template('delivery/dashboard.html', orders=orders)

# Update order status by delivery partner
@routes.route('/delivery/update-order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def delivery_update_order(order_id):
    if not current_user.is_delivery_partner:
        abort(403)
    
    order = Order.query.get_or_404(order_id)
    
    # Only allow updating if the order is assigned to an admin
    if order.assigned_admin_id is None:
        flash('This order has not been claimed by an admin yet.')
        return redirect(url_for('routes.delivery_dashboard'))
    
    form = UpdateOrderForm(obj=order)
    
    # Limit delivery partner to only set "shipped" or "delivered" status
    form.status.choices = [('shipped', 'Shipped'), ('delivered', 'Delivered')]
    
    if form.validate_on_submit():
        order.status = form.status.data
        db.session.commit()
        flash('Order status updated!')
        return redirect(url_for('routes.delivery_dashboard'))
    
    return render_template('delivery/update_order.html', form=form, order=order)


# Modify the city route to accept a brand parameter
@routes.route('/city/<admin_username>')
def city(admin_username):
    # Pass the admin_username to the city template
    return render_template('city.html', admin_username=admin_username)

## Update the brand_page route to match the new URL structure
# Update the brand_page route in routes.py
@routes.route('/<admin_username>/<city>/<area>')
def brand_page(admin_username, city, area):
    # Find the admin user by username
    admin = User.query.filter_by(username=admin_username, is_admin=True).first_or_404()
    
    # Format location for display
    formatted_city = city.replace('-', ' ').title()
    formatted_area = area.replace('-', ' ').title()
    formatted_location = f"{formatted_area}, {formatted_city}"
    
    # Get products by this admin
    # Use a more flexible search approach with individual ilike conditions
    products = Product.query.filter_by(admin_id=admin.id).filter(
        db.or_(
            Product.location.ilike(f"%{formatted_area}%"),
            Product.location.ilike(f"%{area}%")
        )
    ).all()
    
    # Get brand name (for display purposes)
    brand_name = "Zara" if admin_username == "admin" else "Marks & Spencer" if admin_username == "admin2" else "Westside" if admin_username == "admin3" else admin_username
    
    return render_template('brand.html', products=products, brand_name=brand_name, admin=admin, location=formatted_location)

# Keep the existing route for backward compatibility
@routes.route('/brand/<admin_username>/<location>')
def legacy_brand_page(admin_username, location):
    # Redirect to the home page or city selection if accessed via old URL
    return redirect(url_for('routes.city', admin_username=admin_username))


# Remove the old city route (or keep it as a redirect)
@routes.route('/city')
def city_redirect():
    # Redirect to home page if accessed directly
    return redirect(url_for('routes.home'))

# Product detail page
@routes.route('/product/<int:product_id>')
def product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

# Login route
@routes.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Debug print
        print(f"Login attempt for username: {form.username.data}")
        
        user = User.query.filter_by(username=form.username.data).first()
        
        if not user:
            print(f"No user found with username: {form.username.data}")
            # Print all usernames for verification
            all_users = User.query.all()
            for u in all_users:
                print(f"Existing user: {u.username}, Is Admin: {u.is_admin}")
            
            flash('Invalid username or password')
            return render_template('login.html', form=form)
        
        # Debug password check
        from werkzeug.security import check_password_hash
        is_password_correct = check_password_hash(user.password, form.password.data)
        print(f"Password check for {form.username.data}: {is_password_correct}")
        print(f"User admin status: {user.is_admin}")
        
        if is_password_correct:
            login_user(user)
            if user.is_admin:
                return redirect(url_for('routes.admin_dashboard'))
            return redirect(url_for('routes.home'))
        
        flash('Invalid username or password')
    return render_template('login.html', form=form)

# Logout route
@routes.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.home'))

# Add to cart route
@routes.route('/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    
    # Check if product already in cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Added to cart!')
    return redirect(url_for('routes.product', product_id=product_id))



# View cart route
@routes.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = 0
    cart_products = []
    
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            item_total = product.price * item.quantity
            total += item_total
            cart_products.append({
                'product': product,
                'quantity': item.quantity,
                'total': item_total
            })
    
    return render_template('cart.html', cart_products=cart_products, total=total)

# Checkout route
@routes.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('routes.cart'))
    
    # Calculate total and prepare cart products for display
    total = 0
    cart_products = []
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            item_total = product.price * item.quantity
            total += item_total
            cart_products.append({
                'product': product,
                'quantity': item.quantity,
                'total': item_total
            })
    
    form = CheckoutForm()
    
    if form.validate_on_submit():
        # Create order
        order = Order(user_id=current_user.id, total_price=total)
        db.session.add(order)
        db.session.flush()  # To get the order ID
        
        # Create order items
        for item in cart_items:
            product = Product.query.get(item.product_id)
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                price=product.price
            )
            db.session.add(order_item)
        
        # Clear cart
        for item in cart_items:
            db.session.delete(item)
        
        db.session.commit()
        flash('Order placed successfully!')
        return redirect(url_for('routes.my_orders'))
    
    return render_template('checkout.html', form=form, cart_products=cart_products, total=total)
# ADMIN ROUTES
# Admin dashboard
@routes.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
    
    # Get only products created by this admin
    products = Product.query.filter_by(admin_id=current_user.id).all()
    
    # Get only orders assigned to this admin or unassigned orders
    orders = Order.query.filter(
        (Order.assigned_admin_id == current_user.id) | 
        (Order.assigned_admin_id == None)
    ).all()
    
    return render_template('admin/dashboard.html', 
                           products=products, 
                           orders=orders, 
                           unassigned_orders=Order.query.filter_by(assigned_admin_id=None).all())

# Add product route
@routes.route('/admin/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        abort(403)
    
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            gender_tag=form.gender_tag.data,  # Add gender tag
            size=form.size.data,
            location=form.location.data,
            admin_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!')
        return redirect(url_for('routes.admin_dashboard'))
    
    return render_template('admin/add_product.html', form=form)

@routes.route('/admin/claim-order/<int:order_id>', methods=['POST'])
@login_required
def claim_order(order_id):
    if not current_user.is_admin:
        abort(403)
    
    order = Order.query.get_or_404(order_id)
    
    # Only allow claiming if the order is not already assigned
    if order.assigned_admin_id is None:
        order.assigned_admin_id = current_user.id
        db.session.commit()
        flash('Order assigned to you successfully!')
    else:
        flash('This order is already assigned to an admin.')
    
    return redirect(url_for('routes.admin_dashboard'))

@routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('routes.home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username already exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.')
            return render_template('register.html', form=form)
        
        # Create new user
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data, 
            password=hashed_password, 
            is_admin=False,
            gender=form.gender.data  # Save the gender information
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.')
        return redirect(url_for('routes.login'))
    
    return render_template('register.html', form=form)

# User orders route
@routes.route('/my-orders')
@login_required
def my_orders():
    if current_user.is_admin:
        return redirect(url_for('routes.admin_dashboard'))
        
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    # Get order items for each order
    order_details = []
    for order in orders:
        items = OrderItem.query.filter_by(order_id=order.id).all()
        order_products = []
        for item in items:
            product = Product.query.get(item.product_id)
            order_products.append({
                'product': product,
                'quantity': item.quantity,
                'price': item.price
            })
        order_details.append({
            'order': order,
            'products': order_products
        })
    
    return render_template('my_orders.html', order_details=order_details)

# Update order status
@routes.route('/admin/update-order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def update_order(order_id):
    if not current_user.is_admin:
        abort(403)
    
    order = Order.query.get_or_404(order_id)
    
    # Check if the order is assigned to this admin
    if order.assigned_admin_id is not None and order.assigned_admin_id != current_user.id:
        flash('You can only update orders assigned to you.')
        return redirect(url_for('routes.admin_dashboard'))
    
    form = UpdateOrderForm(obj=order)
    
    if form.validate_on_submit():
        order.status = form.status.data
        # If updating status, automatically assign the order to this admin if not already assigned
        if order.assigned_admin_id is None:
            order.assigned_admin_id = current_user.id
        db.session.commit()
        flash('Order status updated!')
        return redirect(url_for('routes.admin_dashboard'))
    
    return render_template('admin/update_order.html', form=form, order=order)
