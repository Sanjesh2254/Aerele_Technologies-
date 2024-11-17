
from flask_wtf import FlaskForm
from Namma_Kadai.models import Item
from wtforms.validators import DataRequired, Email, Length,EqualTo,NumberRange
from wtforms import StringField, IntegerField, FloatField, PasswordField, SubmitField,SelectField,EmailField


class RegistrationForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Length(min=5, max=150)])
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=2, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(min=5, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Login')

class CompanyForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=2, max=150)])
    rate = FloatField('Rate', validators=[DataRequired()])
    submit = SubmitField('Add Company')

class ItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired(), Length(min=2, max=150)])
    qty = IntegerField('Quantity', validators=[DataRequired()],default=0)
    rate = FloatField('Rate', validators=[DataRequired(), NumberRange(min=0)])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Add Item')

class PurchaseForm(FlaskForm):
    item_id = SelectField('Select Item', coerce=int, validators=[DataRequired()], render_kw={"id": "item_id"})
    qty = IntegerField('Quantity', validators=[DataRequired()])
    rate = FloatField('Rate', validators=[DataRequired()])
    submit = SubmitField('Add Purchase')

class SalesForm(FlaskForm):
    item_id = SelectField('Item', coerce=int, validators=[DataRequired()])
    qty = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    def __init__(self, *args, **kwargs):
        super(SalesForm, self).__init__(*args, **kwargs)
        self.item_id.choices = [('', 'Select an item')] + [(item.id, item.item_name) for item in Item.query.all()]



