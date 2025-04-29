from django.urls import path
from . import views

urlpatterns = [

    # User urls
    path('', views.home, name='home'),
    # path('base/', views.base, name='base'),

    # User urls
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),

    path('back/', views.back, name='back'),

    # Admin urls

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('admin-users/', views.user_list, name='user_list'),
    path('admin-users/<int:user_id>/', views.view_user, name='view_user'),
    path('admin-users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('admin-users/delete/<int:user_id>/', views.delete_user, name='delete_user'),

    # Business urls
    path('business/', views.business_register, name='business_register'),
    path('business/dashboard/', views.business_dashboard, name='business_dashboard'),

    path('admin-businesses/', views.business_list_admin, name='business_list_admin'),
    path('admin-businesses/<int:business_id>/update/<str:status>/', views.update_business_status, name='update_business_status'),
    path('admin-businesses/<int:business_id>/view/', views.view_business_details, name='view_business_details'),

    path('pending/', views.pending, name='pending'),
    path('rejected/', views.rejected, name='rejected'),

    path('edit-business-dash/', views.edit_business_dash, name='edit_business_dash'),  #edit_business for dashboard

    path('business-edit/<int:business_id>/', views.edit_business, name='edit_business'),
    # path('business-login/', views.business_login, name='business_login'),
    # path('vendor-dashboard/', views.vendor_dashboard, name='vendor_dashboard'),

    #Product urls
    path('products-admin/', views.product_list, name='product_list_admin'),
    path('products-admin/<int:product_id>/', views.view_product_admin, name='view_product_admin'),
    path('products-admin/<int:product_id>/edit-admin/', views.edit_product_admin, name='edit_product_admin'),
    path('products-admin/<int:product_id>/delete-admin/', views.delete_product_admin, name='delete_product_admin'),

    path('products/', views.product_list_business, name='product_list_business'),
    path('products/<int:product_id>/', views.view_product, name='view_product'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('products-products/', views.products, name='products'),
    path('products-add/', views.add_product, name='add_product'),
    path('products-detail/<int:product_id>/', views.product_detail, name='product_detail'),

    # cart
    path('cart/', views.cart_view, name='cart'),
    path('cart-add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart-update/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('clear_cart/', views.clear_cart, name='clear_cart'),

    # order
    path('checkout/', views.checkout, name='checkout'),
    path('business/orders/', views.business_orders, name='business_orders'),
    path('admin-orders/', views.admin_orders, name='admin_orders'),
    path('user-orders/', views.user_orders, name='user_orders'),

    path('user-payment-history/', views.user_payment_history, name='user_payment_history'),
    path('business-payment-history/', views.business_payment_history, name='business_payment_history'),
    path('admin-payment-history/', views.admin_payment_history, name='admin_payment_history'),

    path('update-order-item-status/<int:order_item_id>/<str:status>/', views.update_order_item_status, name='update_order_item_status'),

    # path("test-esewa/", esewa, name="test_esewa"),
    # path('esewa/payment/', views.esewa_payment, name='esewa_payment'),
    # path('esewa/success', views.success, name='esewa_success'),
    # path('esewa/failure', views.failure, name='esewa_failure'),
]

