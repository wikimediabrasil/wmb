import os
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.contrib.auth import logout

from certificates.models import Certificate


# ==================================================================================================================== #
# INITIAL PAGES
# ==================================================================================================================== #
def index(request):
    context = {}
    return render(request, "users/index.html", context)


# ==================================================================================================================== #
# LOGIN
# ==================================================================================================================== #
def login_oauth(request):
    return redirect(reverse("users:social:begin", kwargs={"backend": "mediawiki"}))


def logout_oauth(request):
    logout(request)
    return redirect(reverse("users:index"))

# ======================================================================================================================
# AUXILIAR FUNCTIONS
# ======================================================================================================================
def list_media_files():
    media_root = settings.MEDIA_ROOT
    media_files = []
    for root, dirs, files in os.walk(media_root):
        for file in files:
            filename = str(os.path.join(root, file))
            relative_path = os.path.relpath(filename, media_root)
            media_files.append(relative_path.replace("\\","/"))
    return media_files


def get_used_files():
    used_files = Certificate.objects.values_list('background', flat=True)
    return set(os.path.basename(file) for file in filter(None, used_files))


def delete_unused_files(request):
    media_files = set(list_media_files())
    used_files = get_used_files()
    unused_files = media_files - used_files

    for file in unused_files:
        file_path = os.path.join(settings.MEDIA_ROOT, file)
        if os.path.exists(file_path):
            os.remove(file_path)

    return HttpResponse("Deleted all unused files.")