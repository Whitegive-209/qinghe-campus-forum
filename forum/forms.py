from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Post, Comment


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'nickname', 'password1', 'password2']


class LoginForm(AuthenticationForm):
    error_messages = {'invalid_login': '用户名或密码不正确，请重新输入。', 'inactive': '该账号已停用。'}


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['nickname', 'bio']
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}


class PostForm(forms.ModelForm):
    title = forms.CharField(label='标题', max_length=100, strip=True)
    body = forms.CharField(label='正文', max_length=10000, strip=True, widget=forms.Textarea(attrs={'rows': 12}))

    class Meta:
        model = Post
        fields = ['category', 'title', 'body']


class CommentForm(forms.ModelForm):
    body = forms.CharField(label='评论内容', max_length=1000, strip=True, widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '分享你的想法，友善交流。'}))

    class Meta:
        model = Comment
        fields = ['body']

