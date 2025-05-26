import hashlib
import hmac
import random
import uuid

from django.contrib.sites import requests
from django.core.mail import send_mail

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_exempt
from .models import User, UserRole, Business, Product, ProductCategory, Cart, CartItem, Orders, Order_Item, Payment, \
    Review
from django.http import Http404, HttpResponse
from esewa import EsewaPayment

@csrf_exempt
def home(request):
    return render(request, 'home.html')

@csrf_exempt
def back(request):
    return render(request, 'home.html')



@csrf_exempt
def register_view(request):
    if request.method == 'POST' and not request.session.get('otp_verified'):
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        image = request.FILES.get('image')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('register')

        request.session['register_data'] = {
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'email': email,
            'password': password,
        }

        if image:
            from django.core.files.base import ContentFile
            request.session['image_name'] = image.name
            request.session['image_data'] = image.read().decode('latin1')
            request.session['has_image'] = True
        else:
            request.session['has_image'] = False

        generate_otp(request, email)
        request.session['otp_next_url'] = 'register'
        return redirect('verify_otp')

    elif request.session.get('otp_verified'):
        data = request.session.get('register_data')
        if not data:
            messages.error(request, "Session expired.")
            return redirect('register')

        image = None
        if request.session.get('has_image'):
            from django.core.files.base import ContentFile
            image = ContentFile(
                request.session.get('image_data').encode('latin1'),
                name=request.session.get('image_name')
            )

        user = User(
            image=image,
            first_name=data['first_name'],
            middle_name=data['middle_name'],
            last_name=data['last_name'],
            email=data['email'],
            password=make_password(data['password'])
        )
        user.save()

        for key in ['otp', 'otp_email', 'otp_verified', 'otp_next_url', 'register_data', 'image_name', 'image_data', 'has_image']:
            request.session.pop(key, None)

        messages.success(request, "Registration successful! Please log in.")
        return redirect('login')

    return render(request, 'register.html')


@csrf_exempt
def login_view(request):
    if request.method == 'POST' and not request.session.get('otp_verified'):
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
            if check_password(password, user.password):
                request.session['login_data'] = {
                    'user_id': user.user_id,
                    'email': user.email,
                    'password_ok': True,
                }

                generate_otp(request, email)
                request.session['otp_next_url'] = 'login'
                return redirect('verify_otp')
            else:
                messages.error(request, "Invalid password.")
        except User.DoesNotExist:
            messages.error(request, "Email not registered.")

    elif request.session.get('otp_verified'):
        login_data = request.session.get('login_data')
        if not login_data or not login_data.get('password_ok'):
            messages.error(request, "Session expired or invalid.")
            return redirect('login')

        try:
            user = User.objects.get(user_id=login_data['user_id'])

            request.session['user_id'] = user.user_id
            request.session['role_id'] = user.role_id.role_id
            request.session['email'] = user.email
            request.session['user_role'] = user.role_id.role
            request.session["user_name"] = f"{user.first_name} {user.middle_name + ' ' if user.middle_name else ''}{user.last_name}"

            for key in ['otp', 'otp_email', 'otp_verified', 'otp_next_url', 'login_data']:
                request.session.pop(key, None)

            sesrole = request.session.get('role_id')

            if sesrole == 3 or sesrole == 4:
                return redirect('admin_dashboard')
            else:
                try:
                    business = Business.objects.get(user_id=user.user_id)
                    request.session['business_status'] = business.status
                    request.session['business_id'] = business.business_id
                except Business.DoesNotExist:
                    pass

                messages.success(request, "Login Successful")
                return redirect('home')
        except User.DoesNotExist:
            messages.error(request, "Something went wrong.")
            return redirect('login')

    return render(request, 'login.html')
@csrf_exempt
def logout_view(request):
    request.session.flush()
    messages.success(request, "Logout Successful")
    return redirect('home')

def generate_otp(request, email):
    otp = str(random.randint(100000, 999999))
    request.session['otp'] = otp
    request.session['otp_email'] = email
    request.session['otp_verified'] = False
    request.session['otp_attempts'] = 0


    send_mail(
        subject='Your OTP Code',
        message=f'Your OTP is: {otp}',
        from_email='stilbdrthapa@example.com',
        recipient_list=[email],
        fail_silently=False
    )

@csrf_exempt
def verify_otp_view(request):
    if request.method == 'POST':
        user_otp = request.POST.get('otp')
        session_otp = request.session.get('otp')

        if 'otp_attempts' not in request.session:
            request.session['otp_attempts'] = 0

        if request.session['otp_attempts'] >= 3:
            messages.error(request, "Maximum OTP attempts exceeded. Please try again.")
            for key in ['otp', 'otp_email', 'otp_verified', 'otp_next_url', 'otp_attempts', 'register_data', 'login_data', 'image_name', 'image_data', 'has_image']:
                request.session.pop(key, None)
            return redirect('login')

        if user_otp == session_otp:
            request.session['otp_verified'] = True
            request.session['otp_attempts'] = 0
            return redirect(request.session.get('otp_next_url', 'home'))
        else:
            request.session['otp_attempts'] += 1
            remaining_attempts = 3 - request.session['otp_attempts']
            messages.error(request, f"Invalid OTP. {remaining_attempts} attempts remaining.")
            return redirect('verify_otp')

    return render(request, 'verify_otp.html')


def admin_dashboard(request):
    return render(request, 'admin/admin_dashboard.html')


def profile_view(request):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('login')

    user = User.objects.get(user_id=user_id)

    recent_orders = Orders.objects.filter(user_id=user).order_by('-created_at')[:5]

    order_items = Order_Item.objects.filter(order_id__in=recent_orders).select_related('order_id', 'product_id')

    try:
        business = Business.objects.get(user_id=user)
    except Business.DoesNotExist:
        business = None

    context = {
        'user': user,
        'order_items': order_items,
        'business': business,
    }

    return render(request, 'user/profile.html',context)


@csrf_exempt
def edit_profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.get(user_id=user_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        image = request.FILES.get('image')

        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if old_password and not check_password(old_password, user.password):
            messages.error(request, "Old password is incorrect.")
            return redirect('edit_profile')

        if new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")
            return redirect('edit_profile')

        user.first_name = first_name
        user.middle_name = middle_name
        user.last_name = last_name
        user.email = email

        if image:
            user.image = image

        if new_password:
            user.password = make_password(new_password)

        user.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('profile')

    return render(request, 'user/edit_profile.html', {'user': user})


# admin
@csrf_exempt
def user_list(request):
    user_role = request.session.get('user_role')

    if user_role not in ['staff', 'superuser']:
        raise Http404("Page not found")

    users = User.objects.all()

    if user_role == 'staff':
        users = users.exclude(role_id__in=[3, 4])

    return render(request, 'admin/user_list.html', {'users': users})

@csrf_exempt
def view_user(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    return render(request, 'admin/view_user.html', {'user': user})

@csrf_exempt
def edit_user(request, user_id):
    user = get_object_or_404(User, user_id=user_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        image = request.FILES.get('image')

        if User.objects.exclude(user_id=user_id).filter(email=email).exists():
            messages.error(request, "Email is already used by another user.")
            return redirect('edit_user', user_id=user.user_id)

        user.first_name = first_name
        user.middle_name = middle_name
        user.last_name = last_name
        user.email = email

        if image:
            user.image = image

        user.save()
        messages.success(request, "User details updated successfully.")
        return redirect('user_list')

    return render(request, 'admin/edit_user.html', {'user': user})

@csrf_exempt
def delete_user(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect('user_list')
    return render(request, 'admin/confirm_delete_user.html', {'user': user})


def business_register(request):
    if request.method == 'POST':
        try:
            business_name = request.POST.get('business_name')
            phone_number = request.POST.get('phone_number')
            citizenship_front = request.FILES.get('citizenship_front')
            citizenship_back = request.FILES.get('citizenship_back')

            user_id = request.session.get('user_id')
            role_id = request.session.get('role_id')
            print(role_id)

            if not user_id:
                messages.error(request, "User not logged in.")
                return redirect('login')

            try:
                user = User.objects.get(user_id=user_id)
            except ObjectDoesNotExist:
                messages.error(request, "User does not exist.")
                return redirect('login')

            # Check if user already registered a business
            if Business.objects.filter(user_id=user_id).exists():
                messages.warning(request, "You have already registered a business.")
                return redirect('business_login')

            # Check if business name or phone number is already in use
            if Business.objects.filter(business_name=business_name).exists():
                messages.error(request, "Business name already exists. Please choose a different one.")
                return redirect('business_register')

            if Business.objects.filter(business_phone_number=phone_number).exists():
                messages.error(request, "Phone number already used for another business.")
                return redirect('business_register')

            # Create and save business
            business = Business(
                user_id=user,
                business_name=business_name,
                business_phone_number=phone_number,
                citizenship_front=citizenship_front,
                citizenship_back=citizenship_back
            )
            business.save()

            request.session['business_status'] = business.status
            messages.success(request, "Business registered successfully!")
            return redirect('pending')

        except Exception as e:
            print(f"Error registering business: {e}")
            messages.error(request, "Something went wrong while registering your business. Please try again.")
            return redirect('business_register')

    return render(request, 'business/business_register.html')

def business_dashboard(request):
    role_id = request.session.get('role_id')
    user_id = request.session.get('user_id')
    if role_id == 1:
        if Business.objects.filter(user_id=user_id).exists():
            return redirect('pending')
    elif role_id == 2:
        try:
            business = Business.objects.get(user_id=user_id)
            print("Business found:", business)

            products = Product.objects.filter(business_id=business).order_by('-created_at')[:5]
            order_items = Order_Item.objects.filter(product_id__business_id=business).order_by('-order_id__created_at')[:5]
            payments = Payment.objects.filter(order_id__order_item__product_id__business_id=business).distinct().order_by('-payment_date')[:5]

        except Business.DoesNotExist:
            business = None
            products = []
            order_items = []
            payments = []

        print("Products:", products)
        print("Order Items:", order_items)
        print("Payments:", payments)

        context = {
            'business': business,
            'products': products,
            'order_items': order_items,
            'payments': payments,
        }

        return render(request, 'business/business_login.html', context)

    return render(request, 'business/business_dashboard.html')

def admin_dashboard(request):
    role_id = request.session.get('role_id')
    user_id = request.session.get('user_id')

    # Assuming role_id == 4 means admin
    if role_id not in [3, 4]:
        messages.error(request, "Access denied. Admins only.")
        return redirect('home')

    try:
        admin_user = User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Admin user not found.")
        return redirect('login')

    users = User.objects.all().order_by('-created_at')[:5]
    business = Business.objects.all().order_by('-created_at')[:5]
    products = Product.objects.all().order_by('-created_at')[:5]
    orders = Orders.objects.all().order_by('-created_at')[:5]
    payments = Payment.objects.all().order_by('-payment_date')[:5]

    context = {
        'admin_user': admin_user,
        'users': users,
        'products': products,
        'orders': orders,
        'payments': payments,
        'business': business,
    }

    return render(request, 'admin/admin_dashboard.html', context)

def pending(request):
    user_id = request.session.get('user_id')
    business = Business.objects.get(user_id=user_id)
    return render(request, "business/business_pending.html", {'business': business})



def rejected(request):
    user_id = request.session.get('user_id')
    business = Business.objects.get(user_id=user_id)
    return render(request, "business/business_rejected.html", {'business': business})

def edit_business(request, business_id):
    business = get_object_or_404(Business, business_id=business_id)

    if request.method == 'POST':
        business.business_name = request.POST.get('business_name')
        business.business_phone_number = request.POST.get('business_phone_number')
        if 'citizenship_front' in request.FILES:
            business.citizenship_front = request.FILES['citizenship_front']

        if 'citizenship_back' in request.FILES:
            business.citizenship_back = request.FILES['citizenship_back']

        business.status = 'Reapplied'
        business.save()
        return redirect(rejected)

    return render(request, 'business/edit_business.html', {'business': business})

def edit_business_dash(request):
    user_id = request.session.get('user_id')

    try:
        business = Business.objects.get(user_id=user_id)
    except Business.DoesNotExist:
        business = None

    if request.method == 'POST':
        business_name = request.POST.get('business_name')
        business_phone_number = request.POST.get('business_phone_number')

        if business:
            if Business.objects.filter(business_phone_number=business_phone_number).exclude(business_id=business.business_id).exists():
                messages.error(request, 'This phone number is already associated with another business.')
            else:
                business.business_name = business_name
                business.business_phone_number = business_phone_number
                business.save()
                (messages.success(request, 'Business Detail updated'))
                return redirect('business_dashboard')

    return render(request, 'business/edit_business.html', {'business': business})

@csrf_exempt
def business_list_admin(request):
    businesses = Business.objects.select_related('user_id').all()
    return render(request, 'admin/business_list.html', {'businesses': businesses})

def update_business_status(request, business_id, status):
    business = get_object_or_404(Business, pk=business_id)
    user = business.user_id

    if status in ['Approved', 'Rejected', 'Pending','Reapplied']:
        business.status = status
        request.session['business_status'] = business.status
        business_status = request.session.get('business_status')

        print(business_status)
        business.save()

        if status == 'Approved':
            user.role_id = UserRole.objects.get(role_id=2)
            user.save()

        else:
            user.role_id = UserRole.objects.get(role_id=1)
            user.save()

    return redirect('business_list_admin')


@csrf_exempt
def view_business_details(request, business_id):
    business = get_object_or_404(Business, business_id=business_id)
    return render(request, 'admin/business_detail.html', {'business': business})

@csrf_exempt
def products(request):
    user_id = request.session.get('user_id')
    products = Product.objects.filter(quantity__gte=1)
    categories = ProductCategory.objects.all()

    business = Business.objects.filter(user_id=user_id).first()

    if business:
        products = products.exclude(business_id=business.business_id)

    search_query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    sort_by = request.GET.get('sort_by', '')

    print(f"Search Query: {search_query}")
    print(f"Category ID: {category_id}")
    print(f"Sort By: {sort_by}")

    if search_query:
        products = products.filter(product_name__icontains=search_query)
        print(f"Filtered Products by Search: {products}")

    if category_id:
        products = products.filter(category_id=category_id)
        print(f"Filtered Products by Category: {products}")

    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name_asc':
        products = products.order_by('product_name')
    elif sort_by == 'name_desc':
        products = products.order_by('-product_name')

    print(f"Final Product List: {products}")

    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'sort_by': sort_by,
    }

    return render(request, 'products/products.html', context)



def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    user_id= request.session.get('user_id')
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating and comment:
            try:
                review = Review.objects.create(
                    product=product,
                    user=user_id,
                    rating=int(rating),
                    comment=comment
                )
                messages.success(request, 'Thank you for your review!')
            except Exception as e:
                messages.error(request, f"An error occurred while submitting your review: {e}")
        else:
            messages.error(request, 'Please fill out both rating and comment fields.')

        return redirect('product_detail', product_id=product_id)

    reviews = Review.objects.filter(product=product)

    return render(request, 'products/product_detail.html', {
        'product': product,
        'reviews': reviews,
    })

csrf_exempt
def product_list(request):
    search_name = request.GET.get('search_name', '')
    category_id = request.GET.get('category', '')
    price_sort = request.GET.get('price_sort', '')

    products = Product.objects.all()

    if search_name:
        products = products.filter(product_name__icontains=search_name)

    if category_id:
        products = products.filter(category_id=category_id)

    if price_sort == 'asc':
        products = products.order_by('price')
    elif price_sort == 'desc':
        products = products.order_by('-price')

    categories = ProductCategory.objects.all()

    return render(request, 'admin/products_list.html', {
        'products': products,
        'categories': categories,
        'search_name': search_name,
        'category_id': category_id,
        'price_sort': price_sort
    })

def view_product_admin(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    return render(request, 'admin/view_product.html', {'product': product})

def edit_product_admin(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)

    if request.method == "POST":
        product.product_name = request.POST.get('product_name')
        product.price = request.POST.get('price')
        product.quantity = request.POST.get('quantity')
        product.product_description = request.POST.get('product_description')
        product.category_id_id = request.POST.get('category_id')  # note the _id if using FK
        if request.FILES.get('product_img'):
            product.product_img = request.FILES.get('product_img')
        product.save()
        return redirect('product_list_admin')

    categories = ProductCategory.objects.all()
    return render(request, 'admin/edit_product.html', {
        'product': product,
        'categories': categories
    })

def delete_product_admin(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    return redirect('product_list_admin')

@csrf_exempt
def product_list_business(request):
    try:
        user_id = request.session.get('user_id')
        business = Business.objects.get(user_id=user_id)
    except Business.DoesNotExist:
        business = None

    if business:
        products = Product.objects.filter(business_id=business.business_id)
    else:
        products = Product.objects.none()

    search_name = request.GET.get('search_name', '').strip()
    category_id = request.GET.get('category', '').strip()
    price_sort = request.GET.get('price_sort', '').strip()

    if search_name:
        products = products.filter(product_name__icontains=search_name)

    if category_id:
        try:
            products = products.filter(category_id=int(category_id))
        except ValueError:
            pass

    # Apply price sorting
    if price_sort == 'asc':
        products = products.order_by('price')
    elif price_sort == 'desc':
        products = products.order_by('-price')

    # Fetch all categories for dropdown
    categories = ProductCategory.objects.all()

    return render(request, 'products/products_list.html', {
        'products': products,
        'categories': categories,
        'search_name': search_name,
        'category_id': category_id,
        'price_sort': price_sort,
    })


def view_product(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    return render(request, 'products/view_product.html', {'product': product})

def edit_product(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)

    if request.method == "POST":
        product.product_name = request.POST.get('product_name')
        product.price = request.POST.get('price')
        product.quantity = request.POST.get('quantity')
        product.product_description = request.POST.get('product_description')
        product.category_id_id = request.POST.get('category_id')  # note the _id if using FK
        if request.FILES.get('product_img'):
            product.product_img = request.FILES.get('product_img')
        product.save()
        return redirect('product_list_business')

    categories = ProductCategory.objects.all()
    return render(request, 'products/edit_product.html', {
        'product': product,
        'categories': categories
    })

def delete_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    return redirect('product_list_business')

@csrf_exempt
def add_product(request):
    user_id = request.session.get('user_id')
    try:
        user_business = Business.objects.get(user_id=user_id)
    except Business.DoesNotExist:
        return render(request,'business/business_register.html')

    categories = ProductCategory.objects.all()

    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        name = request.POST.get('product_name')
        description = request.POST.get('product_description')
        price = request.POST.get('price')
        quantity = request.POST.get('quantity')
        image = request.FILES.get('product_img')

        Product.objects.create(
            business_id=user_business,
            category_id=ProductCategory.objects.get(pk=category_id),
            product_name=name,
            product_description=description,
            price=price,
            quantity=quantity,
            product_img=image
        )
        return redirect('product_list_business')

    return render(request, 'products/add_product.html', {
        'categories': categories,
        'businesses': [user_business]  # still pass for dropdown use
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    return render(request, 'products/product_detail.html', {'product': product})


def add_to_cart(request, product_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('product_detail', product_id=product_id)

    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please log in to add items to your cart.")
        return redirect('login')

    user_id = get_object_or_404(User, pk=user_id)
    product_id = get_object_or_404(Product, pk=product_id)

    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            raise ValueError("Quantity must be at least 1.")
    except ValueError as e:
        messages.error(request, f"Invalid quantity: {e}")
        return redirect('product_detail', product_id=product_id)

    try:
        cart_id = Cart.objects.get(user_id=user_id)
    except Cart.DoesNotExist:
        cart_id = Cart.objects.create(user_id=user_id) # A new cart has been created


    cart_item, created = CartItem.objects.get_or_create(
        cart_id=cart_id,
        product_id=product_id,
        defaults={
            'quantity': quantity,
            'price': product_id.price,
            'subtotal': product_id.price * quantity
        }
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.subtotal = cart_item.price * cart_item.quantity
        cart_item.save()

    messages.success(request, f"{product_id.product_name} has been added to your cart.")

    return redirect('products')

def cart_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect('login')

    user_id = get_object_or_404(User, pk=user_id)
    cart_id, created = Cart.objects.get_or_create(user_id=user_id)
    cart_items = CartItem.objects.filter(cart_id=cart_id)


    cart_total = 0
    for item in cart_items:
        item.subtotal = item.product_id.price * item.quantity
        cart_total += item.subtotal

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
    }

    return render(request, 'products/cart.html', context)

def remove_from_cart(request, cart_item_id):
    user_id = request.session.get('user_id')
    cart_id = Cart.objects.get(user_id=user_id)
    cart_item = get_object_or_404(CartItem,cart_item_id=cart_item_id, cart_id=cart_id)
    cart_item.delete()
    return redirect('cart')

@csrf_exempt
def update_cart(request):
    if request.method == 'POST':
        user_id = request.session.get("user_id")

        cart_id = get_object_or_404(Cart, user_id=user_id)

        for key, value in request.POST.items():
            if key.startswith('quantity_'):
                try:
                    cart_item_id = int(key.split('_')[1])
                    quantity = int(value)

                    cart_item = get_object_or_404(CartItem, cart_item_id=cart_item_id, cart_id=cart_id)

                    if quantity > 0:
                        cart_item.quantity = quantity
                        cart_item.save()
                    else:
                        continue

                    cart_item.subtotal = cart_item.price * cart_item.quantity
                    cart_item.save()

                except (CartItem.DoesNotExist, ValueError):
                    continue

        messages.success(request, "Cart updated successfully.")
        return redirect('cart')


def clear_cart(request):
        user_id = request.session.get('user_id')

        if not user_id:
            messages.error(request, "Please log in to clear your cart.")
            return redirect('login')

        cart_id = get_object_or_404(Cart, user_id=user_id)

        CartItem.objects.filter(cart_id=cart_id).delete()

        messages.success(request, "All items have been removed from your cart.")
        return redirect('cart')



def admin_orders(request):
    order_items = Order_Item.objects.all()

    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    search = request.GET.get('search', '')

    if status:
        order_items = order_items.filter(status=status)

    if start_date and end_date:
        order_items = order_items.filter(order_id__created_at__range=[start_date, end_date])

    if search:
        order_items = order_items.filter(product_id__product_name__icontains=search)

    context = {
        'order_items': order_items,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
        'search': search,
    }

    return render(request, 'admin/admin_order.html', context)


def business_orders(request):
    user_id = request.session.get("user_id")
    business = Business.objects.get(user_id=user_id)

    products = Product.objects.filter(business_id=business)

    order_items = Order_Item.objects.filter(product_id__in=products).select_related('order_id', 'product_id', 'order_id__user_id')

    search = request.GET.get('search', '')
    if search:
        order_items = order_items.filter(product_id__product_name__icontains=search)

    status = request.GET.get('status', '')
    if status:
        order_items = order_items.filter(status=status)

    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date and end_date:
        order_items = order_items.filter(order_id__created_at__range=[start_date, end_date])

    context = {
        'order_items': order_items,
        'business': business,
        'search': search,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'business/business_order.html', context)


def user_orders(request):
    user_id = request.session.get("user_id")

    orders = Orders.objects.filter(user_id=user_id)

    order_items = Order_Item.objects.filter(order_id__in=orders).select_related('order_id', 'product_id')

    search = request.GET.get('search', '')
    if search:
        order_items = order_items.filter(product_id__product_name__icontains=search)

    status = request.GET.get('status', '')
    if status:
        order_items = order_items.filter(status=status)

    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date and end_date:
        order_items = order_items.filter(order_id__created_at__range=[start_date, end_date])

    context = {
        'order_items': order_items,
        'search': search,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'user/user_orders.html', context)


def update_order_item_status(request, order_item_id, status):
    valid_statuses = ['Pending', 'Processing', 'Delivering', 'Completed', 'Cancelled']
    item = get_object_or_404(Order_Item, pk=order_item_id)
    user_role=request.session.get('user_role')
    business_id=request.session.get('business_id')
    user_id = request.session.get('user_id')

    if status in valid_statuses:
        item.status = status
        item.save()
        messages.success(request, f"Status updated to {status}.")
    else:
        messages.error(request, "Invalid status.")


    if user_role in ["superuser", "staff"]:
        return redirect('admin_orders')

    elif user_role == "vendor":
        try:
            business = Business.objects.get(user_id=user_id)
        except Business.DoesNotExist:
            return redirect('user_orders')

        business_prod = Product.objects.filter(business_id=business.business_id)
        is_business_order = Order_Item.objects.filter(order_item_id=order_item_id, product_id__in=business_prod).exists()

        if is_business_order:
            return redirect('business_orders')
        else:
            return redirect('user_orders')

    else:
        return redirect('user_orders')

def user_payment_history(request):
    user_id = request.session.get('user_id')
    orders = Orders.objects.filter(user_id=user_id)
    payments = Payment.objects.filter(order_id__in=orders)

    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    payment_method = request.GET.get('payment_method', '')
    search = request.GET.get('search', '')

    if status:
        payments = payments.filter(status=status)

    if start_date and end_date:
        payments = payments.filter(payment_date__range=[start_date, end_date])

    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    matched_order_items = None
    if search:
        matched_order_items = Order_Item.objects.filter(
            product_id__product_name__icontains=search,
            order_id__user_id=user_id
        )

    filtered_payments = []
    seen_payment_order_items = set()

    for payment in payments:
        order_items = payment.order_id.order_item_set.all()  # <- now correct

        filtered_order_items = []

        for order_item in order_items:

            if search:
                if not matched_order_items.filter(pk=order_item.pk).exists():
                    continue

            payment_order_item_key = (payment.order_id, order_item.order_item_id)
            if payment_order_item_key not in seen_payment_order_items:
                filtered_order_items.append(order_item)
                seen_payment_order_items.add(payment_order_item_key)

        if filtered_order_items:
            filtered_payments.append({
                'payment': payment,
                'order_items': filtered_order_items
            })

    return render(request, 'user/payment_history.html', {
        'payments': filtered_payments,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
        'payment_method': payment_method,
        'search': search,
    })


def business_payment_history(request):

    payments = Payment.objects.all()
    business_id = request.session.get('business_id')

    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    payment_method = request.GET.get('payment_method', '')
    search = request.GET.get('search', '')

    if status:
        payments = payments.filter(status=status)

    if start_date and end_date:
        payments = payments.filter(payment_date__range=[start_date, end_date])

    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    matched_order_items = None
    if search:
        matched_order_items = Order_Item.objects.filter(
            product_id__product_name__icontains=search,
            product_id__business_id=business_id
        )

    filtered_payments = []
    seen_payment_order_items = set()

    for payment in payments:
        order_items = payment.order_id.order_item_set.filter(
            product_id__business_id=business_id
        )

        filtered_order_items = []

        for order_item in order_items:

            if search:
                if not matched_order_items.filter(pk=order_item.pk).exists():
                    continue

            payment_order_item_key = (payment.order_id, order_item.order_item_id)
            if payment_order_item_key not in seen_payment_order_items:
                filtered_order_items.append(order_item)
                seen_payment_order_items.add(payment_order_item_key)

        if filtered_order_items:
            filtered_payments.append({
                'payment': payment,
                'order_items': filtered_order_items,
                'user_full_name': f"{payment.order_id.user_id.first_name} {payment.order_id.user_id.middle_name or ''} {payment.order_id.user_id.last_name}".strip()
            })

    return render(request, 'business/payment_history.html', {
        'payments': filtered_payments,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
        'payment_method': payment_method,
        'search': search,
    })

def admin_payment_history(request):
    payments = Payment.objects.all()

    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    payment_method = request.GET.get('payment_method', '')
    search = request.GET.get('search', '')

    if status:
        payments = payments.filter(status=status)

    if start_date and end_date:
        payments = payments.filter(payment_date__range=[start_date, end_date])

    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    matched_order_items = None
    if search:
        matched_order_items = Order_Item.objects.filter(
            product_id__product_name__icontains=search
        )

    filtered_payments = []
    seen_payment_order_items = set()

    for payment in payments:
        order_items = payment.order_id.order_item_set.all()

        filtered_order_items = []

        for order_item in order_items:

            if search:
                if not matched_order_items.filter(pk=order_item.pk).exists():
                    continue

            payment_order_item_key = (payment.order_id, order_item.order_item_id)
            if payment_order_item_key not in seen_payment_order_items:
                filtered_order_items.append(order_item)
                seen_payment_order_items.add(payment_order_item_key)

        if filtered_order_items:
            filtered_payments.append({
                'payment': payment,
                'order_items': filtered_order_items,
                'user_full_name': f"{payment.order_id.user_id.first_name} {payment.order_id.user_id.middle_name or ''} {payment.order_id.user_id.last_name}".strip()
            })

    return render(request, 'admin/payment_history.html', {  # <-- Your admin template
        'payments': filtered_payments,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
        'payment_method': payment_method,
        'search': search,
    })


def mark_as_paid(request, payment_id):
    if request.method == 'POST':
        payment = get_object_or_404(Payment, payment_id=payment_id)
        payment.status = 'Paid'
        payment.save()
        messages.success(request, f"Payment ID {payment.payment_id} marked as Paid.")
    return redirect('admin_payment_history')

# def checkout(request):
#     user_id = request.session.get("user_id")
#     if not user_id:
#         messages.error(request, "Please log in to place an order.")
#         return redirect('login')
#
#     cart = get_object_or_404(Cart, user_id=user_id)
#     cart_items = CartItem.objects.filter(cart_id=cart)
#
#     if not cart_items.exists():
#         messages.warning(request, "Your cart is empty.")
#         return redirect('cart')
#
#     if request.method == "POST":
#         full_name = request.POST.get('full_name')
#         phone_number = request.POST.get('phone_number')
#         address_line1 = request.POST.get('address_line1')
#         address_line2 = request.POST.get('address_line2', '')
#         city = request.POST.get('city')
#         payment_method = request.POST.get('payment_method', '').strip().lower()
#
#         if not full_name or not phone_number or not address_line1 or not city or not payment_method:
#             messages.error(request, "Please fill in all required fields.")
#             return redirect('checkout')
#
#         order = Orders.objects.create(
#             user_id_id=user_id,
#             full_name=full_name,
#             phone_number=phone_number,
#             address_line1=address_line1,
#             address_line2=address_line2,
#             city=city,
#         )
#
#         total_amount = 150
#         for item in cart_items:
#             Order_Item.objects.create(
#                 order_id=order,
#                 product_id=item.product_id,
#                 price=item.product_id.price,
#                 quantity=item.quantity,
#                 subtotal  = item.product_id.price * item.quantity,
#                 status="Pending",
#
#             )
#
#             product = item.product_id
#             product.quantity -= item.quantity
#             product.save()
#
#             total_amount += item.product_id.price * item.quantity
#
#         if payment_method == "cash_on_delivery":
#             Payment.objects.create(
#                 order_id=order,
#                 payment_method=payment_method,
#                 amount=total_amount,
#             )
#             cart_items.delete()
#             messages.success(request, "Order placed successfully with Cash on Delivery.")
#             return redirect('home')
#
#         elif payment_method == "esewa":
#
#             Payment.objects.create(
#                 order_id=order,
#                 payment_method=payment_method,
#                 amount=total_amount,
#             )
#             cart_items.delete()
#             messages.success(request, "Order placed successfully with Cash on Delivery.")
#             return redirect('home')
#
#             # return handle_esewa_payment(request, order, total_amount)
#             pass
#
#         else:
#             messages.error(request, "Invalid payment method.")
#             return redirect('checkout')
#
#     return render(request, 'address.html')



def get_cart_and_items(user_id):
    cart = get_object_or_404(Cart, user_id=user_id)
    cart_items = CartItem.objects.filter(cart_id=cart)
    return cart, cart_items

def validate_checkout_form(post_data):
    required_fields = ['full_name', 'phone_number', 'address_line1', 'city', 'payment_method']
    for field in required_fields:
        if not post_data.get(field):
            return False
    return True

def create_order(user_id, post_data):
    order = Orders.objects.create(
        user_id_id=user_id,
        full_name=post_data.get('full_name'),
        phone_number=post_data.get('phone_number'),
        address_line1=post_data.get('address_line1'),
        address_line2=post_data.get('address_line2', ''),
        city=post_data.get('city'),
    )
    return order

def process_order_items(order, cart_items):
    total_amount = 0
    for item in cart_items:
        Order_Item.objects.create(
            order_id=order,
            product_id=item.product_id,
            price=item.product_id.price,
            quantity=item.quantity,
            subtotal=item.product_id.price * item.quantity,
            status="Pending",
        )
        product = item.product_id
        product.quantity -= item.quantity
        product.save()

        total_amount += item.product_id.price * item.quantity
    return total_amount

def create_payment(order, payment_method, amount):
    Payment.objects.create(
        order_id=order,
        payment_method=payment_method,
        amount=amount,
    )

def checkout(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please log in to place an order.")
        return redirect('login')

    cart, cart_items = get_cart_and_items(user_id)

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('cart')

    if request.method == "POST":
        if not validate_checkout_form(request.POST):
            messages.error(request, "Please fill in all required fields.")
            return redirect('checkout')

        order = create_order(user_id, request.POST)
        total_amount = process_order_items(order, cart_items)

        payment_method = request.POST.get('payment_method', '').strip().lower()

        if payment_method == "cash_on_delivery":
            create_payment(order, payment_method, total_amount)
            item_lines = []
            for item in cart_items:
                product_name = item.product_id.product_name
                quantity = item.quantity
                price = item.product_id.price
                total_price = price * quantity

                item_lines.append(f"{product_name} - Qty: {quantity} - Price: Rs. {total_price}")

            items_text = "\n".join(item_lines)

            email_body = (
                f"Thank you for your order!\n\n"
                f"Order ID: {order.order_id}\n\n"
                f"Ordered Items:\n{items_text}\n\n"
                f"Total Amount: Rs. {total_amount}\n\n"
                f"Payment Method: Cash on Delivery \n\n"
                f"Your order will be delivered soon. Thank you for shopping with us!"
            )
            user = User.objects.get(user_id=user_id)

            # email = 'stilplaystore@gmail.com'
            email = user.email
            send_mail(
                subject='Your Order Confirmation',
                message=email_body,
                from_email='stilbdrthapa@gmail.com',
                recipient_list=[email],
                fail_silently=False
            )

            cart_items.delete()
            messages.success(request, "Order placed successfully with Cash on Delivery.")

            return redirect('home')

        elif payment_method == "esewa":

            return redirect('confirm_order', order_id=order.order_id)

        else:
            messages.error(request, "Invalid payment method.")
            return redirect('checkout')

    return render(request, 'address.html')

def confirm_order(request, order_id):
    order = Orders.objects.get(order_id=order_id)
    ot = Order_Item.objects.filter(order_id=order_id).first()

    uid=uuid.uuid4()
    payment = EsewaPayment(
        product_code="EPAYTEST",
        success_url=f"http://localhost:8000/success/{order.order_id}/",
        failure_url=f"http://localhost:8000/failure/{order.order_id}/",
        secret_key="8gBm/:&EnhH.1/q"
    )

    payment.create_signature(
        ot.subtotal,
        uid
        # str(order.order_id)

    )
    user_id = request.session.get("user_id")
    user = User.objects.get(user_id=user_id)
    cart, cart_items = get_cart_and_items(user_id)

    item_lines = []
    for item in cart_items:
        product_name = item.product_id.product_name
        quantity = item.quantity
        price = item.product_id.price
        total_price = price * quantity

        item_lines.append(f"{product_name} - Qty: {quantity} - Price: Rs. {total_price}")

    items_text = "\n".join(item_lines)

    email_body = (
        f"Thank you for your order!\n\n"
        f"Order ID: {order.order_id}\n\n"
        f"Ordered Items:\n{items_text}\n\n"
        f"Total Amount: Rs. {ot.subtotal}\n\n"
        f"Payment Method: Esewa \n\n"
        f"Your order will be delivered soon. Thank you for shopping with us!"
    )
    user = User.objects.get(user_id=user_id)

    # email = 'stilplaystore@gmail.com'
    email = user.email
    send_mail(
        subject='Your Order Confirmation',
        message=email_body,
        from_email='stilbdrthapa@gmail.com',
        recipient_list=[email],
        fail_silently=False
    )

    context = {
        'form': payment.generate_form()
    }
    return render(request, 'order/checkout.html', context)


def success(request, order_id):
    order = Orders.objects.get(order_id=order_id)

    verified = True

    if verified:
        payment_exists = Payment.objects.filter(order_id=order).exists()
        if not payment_exists:
            order_items = Order_Item.objects.filter(order_id=order)
            total_amount = sum(item.subtotal for item in order_items)

            Payment.objects.create(
                order_id=order,
                payment_method='esewa',
                amount=total_amount,
                status='Paid'
            )

            cart = Cart.objects.get(user_id=order.user_id)
            CartItem.objects.filter(cart_id=cart).delete()

        messages.success(request, "Payment successful and order confirmed!")
        return render(request, 'home.html')

    else:
        messages.error(request, "Payment verification failed.")
        return redirect('failure', order_id=order_id)

def failure(request):
    messages.error(request, "Payment failed or was cancelled.")
    return render(request, 'home.html')

