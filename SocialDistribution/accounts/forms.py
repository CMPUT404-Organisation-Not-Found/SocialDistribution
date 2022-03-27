from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from django.db import models
from django.core.validators import URLValidator

from myapp.models import Author


class AuthorInfoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['github'].widget.attrs.update({
            'class':
            'form-control',
            'required':
            '',
            'name':
            'github',
            'id':
            'github',
            'type':
            'url',
            'placeholder':
            'https://github.com/cuddles'
        })
        self.fields['profileImage'].widget.attrs.update({
            'class':
            'form-control',
            'required':
            'true',
            'name':
            'profileImage',
            'id':
            'profileImage',
            'type':
            'text',
            'placeholder':
            'https://www.imgur.com/dj2kjdf',
        })

        #TODO: Add cleaned profilePIcture & github methods
    class Meta:
        model = Author
        fields = (
            'profileImage',
            'github',
        )


class SignUpForm(UserCreationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'required': '',
            'name': 'username',
            'id': 'username',
            'type': 'text',
            'placeholder': 'Cuddles',
            'maxlength': '16',
            'minlength': '6',
        })
        self.fields['email'].widget.attrs.update({
            'class':
            'form-control',
            'required':
            '',
            'name':
            'email',
            'id':
            'email',
            'type':
            'text',
            'placeholder':
            'user@email.com',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'required': '',
            'name': 'password1',
            'id': 'password1',
            'type': 'password',
            'placeholder': 'password',
            'maxlength': '22',
            'minlength': '3',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'required': '',
            'name': 'password2',
            'id': 'password2',
            'type': 'password',
            'placeholder': 'confirm password',
            'maxlength': '22',
            'minlength': '3',
        })

        username = forms.CharField(max_length=20, label=False)
        email = forms.CharField(max_length=100)

        def clean_username(self, *args, **kwargs):
            try:
                user = User.objects.get(
                    username=self.clean_data.get('username'))
                print(user)
            except Exception:
                raise ValidationError("Username already in use.")

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'password1',
            'password2',
        )