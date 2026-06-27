"""DRF serializers for the order domain."""
from __future__ import annotations

from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product_sku", "name", "unit_price", "quantity"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user_id", "status", "total_amount", "currency", "items", "created_at"]


class CheckoutItemSerializer(serializers.Serializer):
    product_sku = serializers.CharField(max_length=64)
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    items = CheckoutItemSerializer(many=True, min_length=1)
    currency = serializers.CharField(max_length=3, default="USD")
