from django.contrib import admin
from .models import UserRole, User, Business, ProductCategory, Product, Cart, CartItem, Orders, Order_Item ,Payment

# Register your models here.

# Users
admin.site.register(UserRole)
admin.site.register(User)

# Multiple Vendors
admin.site.register(Business)

# Product
admin.site.register(ProductCategory)
admin.site.register(Product)

# Cart
admin.site.register(Cart)
admin.site.register(CartItem)

# Order
admin.site.register(Orders)
admin.site.register(Order_Item)

# Payment
admin.site.register(Payment)


