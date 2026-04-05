import stripe
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
import models
from auth import get_current_user
 
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID       = os.getenv("STRIPE_PRICE_ID")
FRONTEND_URL          = os.getenv("FRONTEND_URL", "http://localhost:3000")
 
router = APIRouter(prefix="/stripe", tags=["stripe"])
 
@router.post("/create-checkout")
def create_checkout(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{FRONTEND_URL}/dashboard?upgraded=true",
            cancel_url=f"{FRONTEND_URL}/dashboard?cancelled=true",
            metadata={"user_id": str(current_user.id)},
            customer_email=current_user.email or None,
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    payload   = await request.body()
    sig_header = request.headers.get("stripe-signature")
 
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Webhook inválido")
 
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"]["user_id"])
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.is_pro = True
            db.commit()
 
    elif event["type"] in ["customer.subscription.deleted", "customer.subscription.paused"]:
        customer_id = event["data"]["object"]["customer"]
        # Buscar usuario por customer (si lo guardamos en el futuro)
        # Por ahora lo dejamos para la siguiente iteración
        pass
 
    return {"status": "ok"}