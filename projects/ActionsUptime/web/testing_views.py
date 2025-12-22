import json
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt


def testing_view__get_success(request):
    if request.method == "GET":
        return HttpResponse("Success")
    return HttpResponseNotFound("Failure")


def testing_view__get_failure(request):
    if request.method == "GET":
        return HttpResponseNotFound("Failure")
    return HttpResponse("Success")


@csrf_exempt
def testing_view__post_success(request):
    if request.method == "POST":
        return HttpResponse("Success")
    return HttpResponseNotFound("Failure")


@csrf_exempt
def testing_view__post_failure(request):
    if request.method == "POST":
        return HttpResponseNotFound("Failure")
    return HttpResponse("Success")


@csrf_exempt
def testing_view__post_json_success(request):
    if request.method == "POST":
        body = json.loads(request.body)
        return HttpResponse(json.dumps(body))
    return HttpResponseNotFound("Failure")


@csrf_exempt
def testing_view__post_body_success(request):
    if request.method == "POST":
        body = request.body
        return HttpResponse('Success')
    return HttpResponseNotFound("Failure")


def testing_view_redirect_get(request):
    if request.method == "GET":
        return redirect(reverse("testing_view__get_success"))
    return HttpResponseNotFound("Failure")


def testing_view__slow_response(request):
    import time
    time.sleep(5)  # Delay for 5 seconds
    return HttpResponse("Slow Response")


def testing_view__custom_header(request):
    if request.headers.get('X-Custom-Header') != 'Test Value':
        return HttpResponseNotFound("Header not found")
    return HttpResponse("Success")


def testing_view__server_error(request):
    return HttpResponse("Server Error", status=500)