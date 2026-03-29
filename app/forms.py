from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, \
    Length
from flask_babel import _, lazy_gettext as _l
from app.models import User


class LoginForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign In'))


class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField(_l('Register'))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_('Please use a different username.'))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_('Please use a different email address.'))


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Request Password Reset'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField(_l('Request Password Reset'))


class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    about_me = TextAreaField(_l('About me'),
                             validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_('Please use a different username.'))


class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    title = StringField(_l('Title'), validators=[DataRequired(), Length(max=140)])
    post = TextAreaField(_l('Say something'), validators=[DataRequired(), Length(max=5000)])
    tags = StringField(_l('Tags (comma separated, e.g. python, flask)'), validators=[Length(max=200)])
    submit = SubmitField(_l('Submit'))


class EditPostForm(FlaskForm):
    title = StringField(_l('Title'), validators=[DataRequired(), Length(max=140)])
    body = TextAreaField(_l('Body'), validators=[DataRequired(), Length(max=5000)])
    tags = StringField(_l('Tags (comma separated)'), validators=[Length(max=200)])
    submit = SubmitField(_l('Save'))


class CommentForm(FlaskForm):
    body   = TextAreaField(_l('Comment'), validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField(_l('Post Comment'))

class EditCommentForm(FlaskForm):
    body   = TextAreaField(_l('Comment'), validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField(_l('Save'))


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l('Current Password'), validators=[DataRequired()])
    new_password = PasswordField(_l('New Password'), validators=[DataRequired()])
    new_password2 = PasswordField(
        _l('Repeat New Password'), validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField(_l('Change Password'))


class ChangeEmailForm(FlaskForm):
    email = StringField(_l('New Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Change Email'))

    def __init__(self, original_email, *args, **kwargs):
        super(ChangeEmailForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError(_('Please use a different email address.'))


class DeleteAccountForm(FlaskForm):
    password = PasswordField(_l('Confirm Password'), validators=[DataRequired()])
    submit = SubmitField(_l('Delete My Account'))
