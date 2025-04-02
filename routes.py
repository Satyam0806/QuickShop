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
    
    # Get orders that have been claimed by admins
    orders = Order.query.filter(
        Order.assigned_admin_id.isnot(None)
    ).order_by(Order.created_at.desc()).all()
    
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
    # URL encode the admin_username for the template to use properly
    from urllib.parse import quote
    encoded_admin = quote(admin_username)
    # Pass the admin_username to the city template
    return render_template('city.html', admin_username=admin_username, encoded_admin=encoded_admin)

## Update the brand_page route to match the new URL structure
@routes.route('/<path:admin_username>/<city>/<area>')
def brand_page(admin_username, city, area):
    # Use the raw admin_username for finding the user (don't replace spaces)
    admin = User.query.filter_by(username=admin_username, is_admin=True).first_or_404()
    
    # Format location for display
    formatted_city = city.replace('-', ' ').title()
    formatted_area = area.replace('-', ' ').title()
    formatted_location = f"{formatted_area}, {formatted_city}"
    
    # Get products by this admin
    # Use a more flexible search approach with individual ilike conditions
    products = Product.query.filter_by(admin_id=admin.id).filter(
        Product.location.ilike(f"%{formatted_location}%")
    ).all()
    
    # If no products found with the exact location, try a more flexible search
    if not products:
        products = Product.query.filter_by(admin_id=admin.id).filter(
            db.or_(
                Product.location.ilike(f"%{formatted_area}%"),
                Product.location.ilike(f"%{formatted_city}%")
            )
        ).all()
    
    # Get brand name (for display purposes)
    brand_name = "Zara" if admin_username == "admin" else "Marks & Spencer" if admin_username == "admin2" else "Westside" if admin_username == "admin3" else admin_username
    
    return render_template('brand.html', products=products, brand_name=brand_name, admin=admin, location=formatted_location)

# Keep the existing route for backward compatibility
@routes.route('/brand/<admin_username>/<location>')
def legacy_brand_page(admin_username, location):
    # Extract city and area from location if possible
    parts = location.split(', ')
    if len(parts) == 2:
        area, city = parts
        area_slug = area.lower().replace(' ', '-')
        city_slug = city.lower().replace(' ', '-')
        return redirect(url_for('routes.brand_page', admin_username=admin_username, city=city_slug, area=area_slug))
    
    # If we can't parse the location, just redirect to the city selection
    return redirect(url_for('routes.city', admin_username=admin_username))


# Remove the old city route (or keep it as a redirect)
@routes.route('/city')
def city_redirect():
    # Redirect to home page if accessed directly
    return redirect(url_for('routes.home'))

@routes.route('/product/<int:product_id>')
def product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Find alternatives if shared_product_id exists
    alternative_outlets = []
    alternative_sizes = []
    same_location_sizes = []
    
    if product.shared_product_id:
        # Find all products with the same shared_product_id in the SAME location
        same_location_sizes = Product.query.filter(
            Product.shared_product_id == product.shared_product_id,
            Product.location == product.location,
            Product.inventory_quantity > 0,
            Product.id != product.id  # Exclude current product
        ).all()
        
        # Find alternatives at other locations
        alternative_outlets = Product.find_at_other_outlets(
            product.shared_product_id,
            product.size,
            product.admin_id,
            product.location
        )
        
        # Get all available sizes for this product at other locations
        all_available = Product.find_available_sizes(product.shared_product_id)
        
        # Convert to a more user-friendly format
        for size, location, admin_id in all_available:
            admin = User.query.get(admin_id)
            brand_name = "Unknown"
            
            if admin:
                if admin.username == "admin":
                    brand_name = "Zara"
                elif admin.username == "admin2":
                    brand_name = "Marks & Spencer"
                elif admin.username == "admin3":
                    brand_name = "Westside"
                else:
                    brand_name = admin.username
            
            # Only add to alternative sizes if it's different from current product
            if size != product.size or location != product.location:
                alternative_sizes.append({
                    'size': size,
                    'location': location, 
                    'brand': brand_name,
                    'admin_id': admin_id
                })
    
    return render_template(
        'product.html', 
        product=product,
        alternative_outlets=alternative_outlets,
        alternative_sizes=alternative_sizes,
        same_location_sizes=same_location_sizes
    )

# Remove item from cart
@routes.route('/remove-from-cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart.')
    
    return redirect(url_for('routes.cart'))

# Update cart item quantity
@routes.route('/update-cart/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    product = Product.query.get_or_404(product_id)
    
    # Check if there's enough inventory
    if product.inventory_quantity < quantity:
        flash(f'Sorry, only {product.inventory_quantity} items available.')
        return redirect(url_for('routes.cart'))
    
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity = quantity
        db.session.commit()
        flash('Cart updated.')
    
    return redirect(url_for('routes.cart'))

# Product detail page
@routes.route('/product/<int:product_id>/<size>')
def product_with_size(product_id, size):
    product = Product.query.get_or_404(product_id)
    
    # Check if this product is available in the requested size
    product_available = True
    if product.size != size or product.inventory_quantity <= 0:
        product_available = False
        
    # If not available, find alternatives
    alternative_outlets = []
    if not product_available:
        alternative_outlets = Product.find_at_other_outlets(
            product.name, 
            size,
            product.admin_id,
            product.location
        )
        
    return render_template(
        'product.html', 
        product=product, 
        selected_size=size,
        product_available=product_available,
        alternative_outlets=alternative_outlets
    )


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
    product = Product.query.get_or_404(product_id)
    
    # Check if there's enough inventory
    if product.inventory_quantity < quantity:
        flash(f'Sorry, only {product.inventory_quantity} items available at this location.')
        return redirect(url_for('routes.product', product_id=product_id))
    
    # Check if product already in cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        # Check if increasing quantity exceeds inventory
        if product.inventory_quantity < (cart_item.quantity + quantity):
            flash(f'Sorry, only {product.inventory_quantity} items available at this location.')
            return redirect(url_for('routes.product', product_id=product_id))
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

# ADMIN ROUTES
@routes.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('routes.cart'))
    
    # Calculate total and prepare cart products for display
    subtotal = 0
    cart_products = []
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            item_total = product.price * item.quantity
            subtotal += item_total
            cart_products.append({
                'product': product,
                'quantity': item.quantity,
                'total': item_total
            })
    
    # Add tax (assuming 7%)
    tax = round(subtotal * 0.07, 2)
    # Fixed delivery fee
    delivery_fee = 5.00
    # Calculate total with tax and delivery
    total = subtotal + tax + delivery_fee
    
    form = CheckoutForm()
    
    if form.validate_on_submit():
        try:
            # Create order with delivery address
            order = Order(
                user_id=current_user.id, 
                total_price=total,
                tax=tax,
                delivery_fee=delivery_fee,
                estimated_delivery_time="Delivered within 2 hours",
                status='pending',
                
                # Delivery address fields
                delivery_full_name=form.full_name.data,
                delivery_address_line1=form.address_line1.data,
                delivery_address_line2=form.address_line2.data or '',
                delivery_city=form.city.data,
                delivery_state=form.state.data,
                delivery_postal_code=form.postal_code.data,
                delivery_phone=form.phone.data,
                
                # Payment information
                payment_card_name=form.card_name.data,
                payment_card_last4=form.card_number.data[-4:],
                payment_expiry_month=form.expiry_month.data,
                payment_expiry_year=form.expiry_year.data
            )
            db.session.add(order)
            db.session.flush()  # To get the order ID
            
            # Create order items with store location
            for item in cart_items:
                product = Product.query.get(item.product_id)
                
                # Reduce inventory quantity
                if product.inventory_quantity < item.quantity:
                    flash(f'Sorry, not enough inventory for {product.name}')
                    db.session.rollback()
                    return redirect(url_for('routes.cart'))
                    
                product.inventory_quantity -= item.quantity
                
                # Determine brand name
                def get_brand_name(admin_username):
                    brand_mapping = {
                        'admin': 'Zara',
                        'admin2': 'Marks & Spencer',
                        'admin3': 'Westside'
                    }
                    return brand_mapping.get(admin_username, admin_username)
                
                # Get the admin for this product
                admin = User.query.get(product.admin_id)
                brand_name = get_brand_name(admin.username) if admin else 'Unknown'
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    price=product.price,
                    store_location=product.location,
                    store_brand=brand_name
                )
                db.session.add(order_item)
            
            # Clear cart
            for item in cart_items:
                db.session.delete(item)
            
            db.session.commit()
            
            # Store order ID in session to redirect to order summary
            session['last_order_id'] = order.id
            
            flash('Order placed successfully!')
            return redirect(url_for('routes.order_summary', order_id=order.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while processing your order: {str(e)}')
            return redirect(url_for('routes.checkout'))
    
    return render_template('checkout.html', 
                          form=form, 
                          cart_products=cart_products, 
                          subtotal=subtotal,
                          tax=tax,
                          delivery_fee=delivery_fee,
                          total=total)
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
# orders summary route
@routes.route('/order-summary/<int:order_id>')
@login_required
def order_summary(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Ensure user can only view their own orders
    if order.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Get order items with product details
    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    
    items_with_details = []
    for item in order_items:
        product = Product.query.get(item.product_id)
        admin = User.query.get(product.admin_id) if product.admin_id else None
        brand_name = "Unknown"
        
        if admin:
            if admin.username == "admin":
                brand_name = "Zara"
            elif admin.username == "admin2":
                brand_name = "Marks & Spencer"
            elif admin.username == "admin3":
                brand_name = "Westside"
            else:
                brand_name = admin.username
        
        items_with_details.append({
            'product': product,
            'quantity': item.quantity,
            'price': item.price,
            'total': item.price * item.quantity,
            'store_location': item.store_location,
            'store_brand': item.store_brand
        })
    
    return render_template(
        'order_summary.html',
        order=order,
        items=items_with_details,
        subtotal=order.total_price - order.tax - order.delivery_fee,
        tax=order.tax,
        delivery_fee=order.delivery_fee
    )
# Add product route
@routes.route('/admin/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        abort(403)
    
    # Get shared_product_id from query param if copying a product
    shared_product_id = request.args.get('copy_product_id', '')
    
    form = ProductForm()
    
    # Pre-fill the shared product ID if provided
    if request.method == 'GET' and shared_product_id:
        form.shared_product_id.data = shared_product_id
        
        # Optionally pre-fill other fields from the original product
        original_product = Product.query.filter_by(shared_product_id=shared_product_id).first()
        if original_product:
            form.name.data = original_product.name
            form.description.data = original_product.description
            form.price.data = original_product.price
            form.image_url.data = original_product.image_url
            form.gender_tag.data = original_product.gender_tag
    
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            image_url=form.image_url.data,
            gender_tag=form.gender_tag.data,
            size=form.size.data,
            location=form.location.data,
            admin_id=current_user.id,
            shared_product_id=form.shared_product_id.data
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
