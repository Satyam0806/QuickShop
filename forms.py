from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FloatField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FloatField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, EqualTo

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
    
class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    price = FloatField('Price', validators=[DataRequired()])
    image_url = StringField('Image URL')
    gender_tag = SelectField('Gender', choices=[('men', 'Men'), ('women', 'Women'), ('unisex', 'Unisex')])
    size = SelectField('Size', choices=[
        ('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL'),
        ('28', '28'), ('30', '30'), ('32', '32'), ('34', '34'), ('36', '36'), ('38', '38'), ('40', '40')
    ])
    location = StringField('Store Location', validators=[DataRequired()])
    # Add shared product ID field
    shared_product_id = StringField('Shared Product ID', description='Use the same ID for identical products across outlets')
    submit = SubmitField('Add Product')
    
class UpdateOrderForm(FlaskForm):
    status = SelectField('Status', choices=[('pending', 'Pending'), ('shipped', 'Shipped'), ('delivered', 'Delivered')])
    submit = SubmitField('Update Status')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Prefer not to say')])
    submit = SubmitField('Sign Up')

class CheckoutForm(FlaskForm):
    # Delivery information
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    address_line1 = StringField('Address Line 1', validators=[DataRequired()])
    address_line2 = StringField('Address Line 2')
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State/Province', validators=[DataRequired()])
    postal_code = StringField('Postal/Zip Code', validators=[DataRequired()])
    country = StringField('Country', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    
    # Payment information (demo only)
    card_name = StringField('Name on Card', validators=[DataRequired()])
    card_number = StringField('Card Number', validators=[DataRequired(), Length(min=16, max=16)])
    expiry_month = SelectField('Expiry Month', choices=[(str(i), str(i)) for i in range(1, 13)], validators=[DataRequired()])
    expiry_year = SelectField('Expiry Year', choices=[(str(i), str(i)) for i in range(2025, 2035)], validators=[DataRequired()])
    cvv = StringField('CVV', validators=[DataRequired(), Length(min=3, max=4)])
    
    submit = SubmitField('Complete Order')
