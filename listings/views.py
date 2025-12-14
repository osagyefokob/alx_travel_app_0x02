import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Payment


CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY", "test-secret-key")
CHAPA_BASE_URL = "https://api.chapa.co/v1/transaction"


@csrf_exempt
def initiate_payment(request):
    """
    Initiates a payment with Chapa API
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    data = request.POST
    amount = data.get("amount")
    booking_reference = data.get("booking_reference")
    email = data.get("email")

    payment = Payment.objects.create(
        booking_reference=booking_reference,
        amount=amount,
        status="Pending"
    )

    payload = {
        "amount": amount,
        "currency": "ETB",
        "email": email,
        "tx_ref": booking_reference,
        "callback_url": "http://localhost:8000/verify-payment/",
        "return_url": "http://localhost:8000/payment-success/"
    }

    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
    }

    response = requests.post(
        f"{CHAPA_BASE_URL}/initialize",
        json=payload,
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        payment.transaction_id = result.get("data", {}).get("tx_ref")
        payment.save()
        return JsonResponse(result)

    return JsonResponse({"error": "Payment initiation failed"}, status=400)


@csrf_exempt
def verify_payment(request, tx_ref):
    """
    Verifies payment status with Chapa API
    """
    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
    }

    response = requests.get(
        f"{CHAPA_BASE_URL}/verify/{tx_ref}",
        headers=headers
    )

    try:
        payment = Payment.objects.get(transaction_id=tx_ref)
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)

    if response.status_code == 200:
        result = response.json()
        status = result.get("data", {}).get("status")

        if status == "success":
            payment.status = "Completed"
        else:
            payment.status = "Failed"

        payment.save()
        return JsonResponse({"status": payment.status})

    return JsonResponse({"error": "Verification failed"}, status=400)
