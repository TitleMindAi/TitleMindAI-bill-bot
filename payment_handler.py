import stripe
import os
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_checkout_session(amount_usd, telegram_id, success_url, cancel_url):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f'TitleMind Processing Credit - ${amount_usd}'
                },
                'unit_amount': int(amount_usd * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        metadata={'telegram_id': str(telegram_id)},
        success_url=success_url,
        cancel_url=cancel_url
    )
    return session.url