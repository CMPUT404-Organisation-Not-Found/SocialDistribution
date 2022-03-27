from pyexpat.errors import messages
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect, render

from accounts.forms import AuthorInfoForm, SignUpForm, UserCreationForm
from myapp.models import Author, Inbox


def signup(request):
    # if request.user.is_authenticated:
    #     return redirect('myapp:postList')  # TODO: Redirect to account page
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        author_form = AuthorInfoForm(request.POST)
        if form.is_valid() and author_form.is_valid():
            # user need to go back to log in
            form.save()
            user = form.save()

            try:
                profile_image_string = author_form.cleaned_data['profileImage']
            except:
                profile_image_string = 'https://www.ibm.com/support/pages/system/files/support/swg/rattech.nsf/0/a857b0395de747c085257bcf0037ccb6/Symptom/0.126.gif'

            github = author_form.cleaned_data['github']
            author = Author(username=user.username,
                            host=f"https://{request.get_host()}/",
                            displayName=user.username,
                            profileImage=profile_image_string,
                            github=github)

            author.save()
            author.id = "http://"+request.get_host()+"/authors/"+str(author.uuid)
            print("author id is "+author.id)
            author.save()
            inbox = Inbox(author=author)
            inbox.save()
            return redirect('/accounts/login')
    else:
        form = SignUpForm()
        author_form = AuthorInfoForm()
    context = {'form': form, 'author_info_form': AuthorInfoForm}
    return render(request, 'registration/signup.html', context)
