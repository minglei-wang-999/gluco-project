from decimal import Decimal

SUBSCRIPTION_PLANS = {
    "trial": {
        "id": "trial",
        "name": "免费试用",
        "duration": "3",
        "price": Decimal("0"),
        "description": "免费试用3天",
        "available": True
    },
    "monthly": {
        "id": "monthly",
        "name": "30天包月",
        "duration": "30",
        "price": Decimal("9.9"),
        "description": "订阅后可使用30天",
        "available": False
    },
    "yearly": {
        "id": "yearly",
        "name": "365天包年",
        "duration": "365",
        "price": Decimal("99"),
        "description": "订阅后可使用365天",
        "available": False
    },
    "lifetime": {
        "id": "lifetime",
        "name": "永久使用",
        "duration": "lifetime",
        "price": Decimal("19.9"),
        "description": "促销价！（促销截止日期：2025-06-15）。可永久使用，无限时间",
        "available": True
    }
} 